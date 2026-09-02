"""Caso de uso para las escrituras sobre la ficha de Google Business Profile.

Es el único punto por el que deben pasar las mutaciones de la ficha: aplica los
guardrails determinísticos de dominio **antes** de tocar la red, de modo que una
publicación mal formada o una respuesta que pisaría otra existente nunca llegue
a la API de Google.
"""

from typing import Any

from src.application.dtos.analytics_dtos import (
    GbpPostRequestDTO,
    GbpReviewReplyRequestDTO,
)
from src.domain.analytics.exceptions import AnalyticsDomainException
from src.domain.analytics.ports import GoogleBusinessProfileDataSourcePort
from src.domain.analytics.services import MarketingActionGuardrailService
from src.domain.analytics.value_objects import MarketingActionType


class PublicarEnFichaGoogleUseCase:
    """Orquesta validación y escritura sobre la ficha de Google Business Profile."""

    def __init__(self, gbp_port: GoogleBusinessProfileDataSourcePort) -> None:
        self._gbp_port = gbp_port

    def publicar(self, request: GbpPostRequestDTO) -> dict[str, Any]:
        """Valida y crea una publicación en la ficha."""
        params: dict[str, Any] = {
            "summary": request.summary,
            "cta_url": request.cta_url,
            "cta_type": request.cta_type,
            "schedule_time": request.schedule_time,
        }

        try:
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_CREATE_POST,
                params=params,
            )
        except AnalyticsDomainException as e:
            return {
                "status": "rejected",
                "action_type": MarketingActionType.GBP_CREATE_POST.value,
                "message": str(e),
                "params": params,
            }

        return self._gbp_port.create_post(
            summary=request.summary,
            cta_url=request.cta_url,
            cta_type=request.cta_type.strip().upper(),
            schedule_time=request.schedule_time,
        )

    def responder_resena(self, request: GbpReviewReplyRequestDTO) -> dict[str, Any]:
        """Valida y publica la respuesta del negocio a una reseña.

        Consulta el estado real de la reseña antes de validar, para que el
        guardrail de sobrescritura se evalúe contra la ficha y no contra lo que
        el agente afirme.
        """
        tiene_respuesta, error = self._resena_ya_respondida(request.review_id)
        if error is not None:
            return error

        params: dict[str, Any] = {
            "review_id": request.review_id,
            "comment": request.comment,
            "overwrite": request.overwrite,
            "tiene_respuesta": tiene_respuesta,
        }

        try:
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_REPLY_REVIEW,
                params=params,
            )
        except AnalyticsDomainException as e:
            return {
                "status": "rejected",
                "action_type": MarketingActionType.GBP_REPLY_REVIEW.value,
                "message": str(e),
                "params": params,
            }

        return self._gbp_port.reply_to_review(
            review_id=request.review_id,
            comment=request.comment,
            overwrite=request.overwrite,
        )

    def _resena_ya_respondida(
        self, review_id: str
    ) -> tuple[bool, dict[str, Any] | None]:
        """Retorna si la reseña ya tiene respuesta, o el error que impidió averiguarlo."""
        listado = self._gbp_port.get_reviews(limit=50)
        if listado.get("status") != "success":
            return False, listado

        for r in listado.get("resenas", []):
            if str(r.get("review_id", "")) == review_id:
                return bool(r.get("tiene_respuesta", False)), None

        return False, {
            "status": "not_found",
            "message": (
                f"La reseña '{review_id}' no aparece entre las 50 más recientes de la ficha."
            ),
        }
