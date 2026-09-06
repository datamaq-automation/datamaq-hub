"""Pure transport-agnostic controller for inbound mail opportunity analysis."""

from src.application.dtos.mail_dto import (
    AnalisisEmailDTO,
    ScanMailRequestDTO,
    ScanMailResponseDTO,
)
from src.application.use_cases.analizar_correos_entrantes import (
    AnalizarCorreosEntrantesUseCase,
)


class MailAnalysisController:
    """Agnostic controller orchestrating the B2B opportunity scan of inbound mail."""

    def __init__(
        self,
        analizar_correos_use_case: AnalizarCorreosEntrantesUseCase,
    ) -> None:
        self.analizar_correos_use_case = analizar_correos_use_case

    def analizar_correos(self, dto: ScanMailRequestDTO) -> ScanMailResponseDTO:
        """Scans the mailbox, scores opportunities and dispatches deduplicated alerts."""
        return self.analizar_correos_use_case.execute(request=dto)

    def analizar_correo(
        self,
        uid: str,
        cuenta: str,
        carpeta: str = "INBOX",
    ) -> AnalisisEmailDTO:
        """Scores a single message without notifying nor writing to the dedup cache."""
        return self.analizar_correos_use_case.analizar_single(
            uid=uid,
            cuenta=cuenta,
            carpeta=carpeta,
        )
