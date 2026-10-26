from enum import StrEnum


class AIErrorCode(StrEnum):
    DISABLED = "AI_DISABLED"
    GATEWAY_UNAVAILABLE = "AI_GATEWAY_UNAVAILABLE"
    AUTH_ERROR = "AI_AUTH_ERROR"
    MODEL_UNAVAILABLE = "AI_MODEL_UNAVAILABLE"
    RATE_LIMITED = "AI_RATE_LIMITED"
    TIMEOUT = "AI_TIMEOUT"
    UPSTREAM_ERROR = "AI_UPSTREAM_ERROR"
    INVALID_RESPONSE = "AI_INVALID_RESPONSE"


ERRORS = {
    AIErrorCode.DISABLED: (503, "La explicación mediante IA está desactivada."),
    AIErrorCode.GATEWAY_UNAVAILABLE: (503, "La pasarela de IA no está disponible."),
    AIErrorCode.AUTH_ERROR: (502, "La pasarela de IA rechazó la autenticación."),
    AIErrorCode.MODEL_UNAVAILABLE: (503, "El modelo configurado no está disponible."),
    AIErrorCode.RATE_LIMITED: (503, "La pasarela de IA alcanzó su límite de solicitudes."),
    AIErrorCode.TIMEOUT: (504, "La explicación excedió el tiempo permitido."),
    AIErrorCode.UPSTREAM_ERROR: (502, "No se pudo obtener la explicación de IA."),
    AIErrorCode.INVALID_RESPONSE: (502, "La respuesta de IA no cumple el contrato de explicación."),
}


class AIError(Exception):
    """Error público cerrado: no almacena respuestas, credenciales ni excepciones HTTP."""

    def __init__(self, code: AIErrorCode):
        self.code = code
        self.status_code, self.message = ERRORS[code]
        super().__init__(self.message)
