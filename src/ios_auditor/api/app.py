from __future__ import annotations

import logging
from collections import Counter
from pathlib import PurePath
from uuid import UUID

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ios_auditor import __version__
from ios_auditor.api.dependencies import (
    get_analysis_repository,
    get_connection_factory,
    get_rule_registry,
)
from ios_auditor.api.errors import ApiError
from ios_auditor.api.full_device_serialization import (
    FullDeviceResponseContractError,
    to_full_device_analysis_response,
)
from ios_auditor.api.repository import InMemoryAnalysisRepository, StoredAnalysis
from ios_auditor.api.schemas import (
    AnalysisCreatedResponse,
    AnalysisResponse,
    DeviceAnalysisRequest,
    ErrorResponse,
    FindingResponse,
    FullDeviceAnalysisResponse,
    HealthResponse,
    RuleEvaluationResponse,
    RuleSummaryResponse,
)
from ios_auditor.collectors import (
    CollectorAuthenticationError,
    CollectorConnectionError,
    CollectorTimeoutError,
    CommandNotAllowedError,
)
from ios_auditor.collectors.netmiko_collector import ConnectionFactory
from ios_auditor.rules import RuleRegistry
from ios_auditor.services import (
    AnalysisError,
    EvidenceBatchValidationError,
    FullDeviceAnalysisContractError,
    OperationalAnalysisError,
    collect_and_analyze_device,
)
from ios_auditor.services.analyzer import (
    EmptyContentError,
    InvalidEncodingError,
    UnanalyzableConfigError,
    analyze_bytes,
)
from ios_auditor.services.serialization import to_primitive


SERVICE_NAME = "ios-auditor"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".cfg", ".conf", ".txt"})
logger = logging.getLogger("ios_auditor.api")

DEVICE_TIMEOUT_CODE = "DEVICE_TIMEOUT"
DEVICE_ANALYSIS_FAILED_CODE = "DEVICE_ANALYSIS_FAILED"
DEVICE_TIMEOUT_MESSAGE = "El dispositivo no respondió dentro del tiempo permitido."
DEVICE_ANALYSIS_FAILED_MESSAGE = (
    "No fue posible completar el análisis del dispositivo."
)
INTERNAL_ERROR_MESSAGE = "Ocurrió un error interno inesperado."

app = FastAPI(
    title="Cisco IOS Auditor API",
    version=__version__,
    description="API local y síncrona para análisis determinista de running-config.",
)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


@app.exception_handler(ApiError)
async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    missing_file = any(
        error.get("type") == "missing" and "file" in error.get("loc", ())
        for error in exc.errors()
    )
    if missing_file:
        return _error_response(422, "MISSING_FILE", "Debe adjuntar el campo 'file'.")
    return _error_response(422, "INVALID_REQUEST", "La solicitud no es válida.")


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "error_interno method=%s path=%s type=%s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return _error_response(500, "INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE)


@app.middleware("http")
async def safe_request_logging(request: Request, call_next):
    response = await call_next(request)
    logger.info(
        "request method=%s path=%s status=%s analysis_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        request.path_params.get("analysis_id", "-"),
    )
    return response


def _sanitize_filename(filename: str | None) -> str:
    if not filename or not filename.strip():
        raise ApiError(400, "EMPTY_FILENAME", "El nombre del archivo está vacío.")
    normalized = filename.strip().replace("\\", "/")
    basename = PurePath(normalized).name
    if not basename or basename in {".", ".."}:
        raise ApiError(400, "EMPTY_FILENAME", "El nombre del archivo está vacío.")
    if PurePath(basename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ApiError(
            415,
            "INVALID_EXTENSION",
            "La extensión permitida debe ser .cfg, .conf o .txt.",
        )
    return basename


def _parse_analysis_id(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ApiError(422, "INVALID_ANALYSIS_ID", "El analysis_id no es un UUID válido.") from exc


def _get_stored(
    value: str, repository: InMemoryAnalysisRepository
) -> StoredAnalysis:
    analysis_id = _parse_analysis_id(value)
    stored = repository.get(analysis_id)
    if stored is None:
        raise ApiError(404, "ANALYSIS_NOT_FOUND", "El análisis solicitado no existe.")
    return stored


def _analysis_response(stored: StoredAnalysis) -> AnalysisResponse:
    evaluations = [to_primitive(item) for item in stored.result.evaluations]
    findings = [to_primitive(item) for item in stored.result.findings]
    status_summary = Counter(item.status.value for item in stored.result.evaluations)
    severity_summary = Counter(item.severity.value for item in stored.result.findings)
    return AnalysisResponse(
        analysis_id=str(stored.analysis_id),
        source_name=stored.source_name,
        sha256=stored.result.sha256,
        created_at=stored.created_at,
        status="COMPLETED",
        evaluations=evaluations,
        findings=findings,
        total_evaluations=len(evaluations),
        total_findings=len(findings),
        status_summary=dict(status_summary),
        finding_severity_summary=dict(severity_summary),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, version=__version__)


@app.get("/api/v1/rules", response_model=list[RuleSummaryResponse])
def list_rules(
    registry: RuleRegistry = Depends(get_rule_registry),
) -> list[RuleSummaryResponse]:
    return [
        RuleSummaryResponse(
            id=rule.metadata.id,
            version=rule.metadata.version,
            name=rule.metadata.name,
            category=rule.metadata.category,
            default_severity=rule.metadata.default_severity,
            description=rule.metadata.description,
            required_sources=list(rule.metadata.required_sources),
        )
        for rule in registry.list_rules(enabled_only=True)
    ]


@app.post(
    "/api/v1/device-analyses",
    response_model=FullDeviceAnalysisResponse,
    status_code=200,
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
def create_device_analysis(
    request: DeviceAnalysisRequest,
    connection_factory: ConnectionFactory = Depends(get_connection_factory),
) -> FullDeviceAnalysisResponse:
    try:
        result = collect_and_analyze_device(
            host=str(request.host),
            port=request.port,
            username=request.username,
            password=request.password.get_secret_value(),
            connection_factory=connection_factory,
        )
        return to_full_device_analysis_response(result)
    except CollectorTimeoutError:
        raise ApiError(
            504,
            DEVICE_TIMEOUT_CODE,
            DEVICE_TIMEOUT_MESSAGE,
        ) from None
    except (
        CollectorAuthenticationError,
        CollectorConnectionError,
        EvidenceBatchValidationError,
        OperationalAnalysisError,
        AnalysisError,
    ):
        raise ApiError(
            502,
            DEVICE_ANALYSIS_FAILED_CODE,
            DEVICE_ANALYSIS_FAILED_MESSAGE,
        ) from None
    except (
        CommandNotAllowedError,
        FullDeviceAnalysisContractError,
        FullDeviceResponseContractError,
    ):
        raise ApiError(500, "INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE) from None
    except Exception:
        raise ApiError(500, "INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE) from None


@app.post(
    "/api/v1/analyses",
    response_model=AnalysisCreatedResponse,
    status_code=201,
)
async def create_analysis(
    file: UploadFile = File(...),
    repository: InMemoryAnalysisRepository = Depends(get_analysis_repository),
    registry: RuleRegistry = Depends(get_rule_registry),
) -> AnalysisCreatedResponse:
    source_name = _sanitize_filename(file.filename)
    try:
        raw = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()

    if len(raw) > MAX_UPLOAD_BYTES:
        raise ApiError(413, "FILE_TOO_LARGE", "El archivo supera el límite de 2 MiB.")

    try:
        result = analyze_bytes(raw, source_name=source_name, registry=registry)
    except EmptyContentError as exc:
        raise ApiError(400, "EMPTY_FILE", "El archivo está vacío.") from exc
    except InvalidEncodingError as exc:
        raise ApiError(400, "INVALID_ENCODING", "El archivo debe ser texto UTF-8 válido.") from exc
    except UnanalyzableConfigError as exc:
        raise ApiError(
            422, "UNANALYZABLE_CONFIG", "La configuración no pudo analizarse."
        ) from exc

    stored = repository.create(source_name=source_name, result=result)
    logger.info(
        "analysis_completed analysis_id=%s source_name=%s evaluations=%s findings=%s",
        stored.analysis_id,
        source_name,
        len(result.evaluations),
        len(result.findings),
    )
    return AnalysisCreatedResponse(**_analysis_response(stored).model_dump())


@app.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: str,
    repository: InMemoryAnalysisRepository = Depends(get_analysis_repository),
) -> AnalysisResponse:
    return _analysis_response(_get_stored(analysis_id, repository))


@app.get(
    "/api/v1/analyses/{analysis_id}/evaluations",
    response_model=list[RuleEvaluationResponse],
)
def get_evaluations(
    analysis_id: str,
    repository: InMemoryAnalysisRepository = Depends(get_analysis_repository),
) -> list[dict]:
    stored = _get_stored(analysis_id, repository)
    return [to_primitive(item) for item in stored.result.evaluations]


@app.get(
    "/api/v1/analyses/{analysis_id}/findings",
    response_model=list[FindingResponse],
)
def get_findings(
    analysis_id: str,
    repository: InMemoryAnalysisRepository = Depends(get_analysis_repository),
) -> list[dict]:
    stored = _get_stored(analysis_id, repository)
    return [to_primitive(item) for item in stored.result.findings]
