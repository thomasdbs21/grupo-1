from uuid import UUID

from fastapi import APIRouter, Depends

from ios_auditor.ai.contracts import AIHealth, ExplanationRequest, ExplanationResponse
from ios_auditor.ai.repository import AIContextRepository
from ios_auditor.ai.service import ExplanationService
from ios_auditor.api.dependencies import get_ai_context_repository, get_ai_service
from ios_auditor.api.errors import ApiError

router = APIRouter()


@router.get("/api/v1/ai/health", response_model=AIHealth)
def ai_health(service: ExplanationService = Depends(get_ai_service)) -> AIHealth:
    return AIHealth(enabled=service.settings.enabled,
                    gateway_reachable=service.settings.enabled and service.provider.reachable(),
                    model_configured=bool(service.settings.model))


@router.post("/api/v1/analyses/{analysis_id}/ai-explanation", response_model=ExplanationResponse)
def explain_analysis(
    analysis_id: UUID,
    request: ExplanationRequest | None = None,
    repository: AIContextRepository = Depends(get_ai_context_repository),
    service: ExplanationService = Depends(get_ai_service),
) -> ExplanationResponse:
    context = repository.get(analysis_id)
    if context is None:
        raise ApiError(404, "ANALYSIS_NOT_FOUND", "El contexto del análisis no existe o expiró.")
    return service.explain(context, request.question if request else None)
