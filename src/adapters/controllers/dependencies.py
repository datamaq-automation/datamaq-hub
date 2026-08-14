"""Dependency injection providers for controllers and use cases."""

from functools import lru_cache

from src.adapters.controllers.health_controller import HealthController
from src.adapters.controllers.receipt_controller import ReceiptController
from src.adapters.controllers.simulation_controller import SimulationController
from src.adapters.gateways.paritaria_json_gateway import ParitariaJsonGateway
from src.adapters.gateways.pdfplumber_extractor_gateway import (
    PdfPlumberExtractorGateway,
)
from src.adapters.gateways.receipt_parsers.parser_registry_gateway import (
    ReceiptParserRegistryGateway,
)
from src.application.use_cases.parse_receipt import ParseReceiptUseCase
from src.application.use_cases.project_salary import ProjectSalaryUseCase
from src.domain.liquidacion.ports import ParitariaRepositoryPort
from src.domain.liquidacion.services import MotorLiquidacionDocenteService
from src.domain.recibos.ports import PDFExtractorPort, ReceiptParserRegistryPort


@lru_cache
def get_pdf_extractor_gateway() -> PDFExtractorPort:
    return PdfPlumberExtractorGateway()


@lru_cache
def get_parser_registry_gateway() -> ReceiptParserRegistryPort:
    return ReceiptParserRegistryGateway()


def get_parse_receipt_use_case() -> ParseReceiptUseCase:
    extractor = get_pdf_extractor_gateway()
    parser_registry = get_parser_registry_gateway()
    return ParseReceiptUseCase(extractor=extractor, parser_registry=parser_registry)


@lru_cache
def get_motor_liquidacion_service() -> MotorLiquidacionDocenteService:
    return MotorLiquidacionDocenteService()


@lru_cache
def get_paritaria_repository_gateway() -> ParitariaRepositoryPort:
    return ParitariaJsonGateway()


def get_project_salary_use_case() -> ProjectSalaryUseCase:
    motor = get_motor_liquidacion_service()
    paritaria_repo = get_paritaria_repository_gateway()
    return ProjectSalaryUseCase(paritaria_repo=paritaria_repo, motor=motor)


def get_health_controller() -> HealthController:
    return HealthController()


def get_receipt_controller() -> ReceiptController:
    use_case = get_parse_receipt_use_case()
    return ReceiptController(parse_use_case=use_case)


def get_simulation_controller() -> SimulationController:
    use_case = get_project_salary_use_case()
    return SimulationController(project_use_case=use_case)
