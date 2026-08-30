"""Tests unitarios del caso de uso ProcesarResumenTarjetaUseCase."""

from datetime import date
from typing import BinaryIO

from src.application.dtos.tarjeta_dto import ResumenTarjetaDTO
from src.application.use_cases.procesar_resumen_tarjeta import (
    ProcesarResumenTarjetaUseCase,
)
from src.domain.tarjetas.entities import ResumenTarjeta, TransaccionTarjeta
from src.domain.tarjetas.ports import TarjetaCreditoParserPort, TarjetaRepositoryPort


class FakeTarjetaParser(TarjetaCreditoParserPort):
    """Parser falso que devuelve un resumen BBVA Visa Gold fijo."""

    def parsear(self, archivo: BinaryIO) -> ResumenTarjeta:
        archivo.read()
        return ResumenTarjeta(
            id_resumen="1097452662-2026-08-27",
            banco="BBVA",
            tarjeta_tipo="VISA",
            tarjeta_categoria="GOLD",
            numero_cuenta="1097452662",
            fecha_cierre=date(2026, 8, 27),
            fecha_vencimiento=date(2026, 9, 7),
            saldo_pesos=144565.27,
            saldo_dolares=0.0,
            pago_minimo=82120.0,
            consumos=(
                TransaccionTarjeta(
                    fecha=date(2026, 8, 10),
                    descripcion="MIRGOR SACIFIA C.08/09 000014",
                    monto_pesos=1500.0,
                    monto_dolares=0.0,
                ),
            ),
        )


class FakeTarjetaRepository(TarjetaRepositoryPort):
    """Repositorio falso que registra las llamadas a guardar."""

    def __init__(self) -> None:
        self.guardados: list[ResumenTarjeta] = []

    def guardar(self, resumen: ResumenTarjeta) -> None:
        self.guardados.append(resumen)

    def obtener_por_id(self, id_resumen: str) -> ResumenTarjeta | None:
        return None

    def obtener_resumenes_vencimiento_cercano(
        self, fecha_limite: date
    ) -> list[ResumenTarjeta]:
        return []


def test_procesar_resumen_mapea_a_dto_y_persiste() -> None:
    parser = FakeTarjetaParser()
    repository = FakeTarjetaRepository()
    use_case = ProcesarResumenTarjetaUseCase(parser=parser, repository=repository)

    resultado = use_case.execute(b"pdf-falso")

    assert isinstance(resultado, ResumenTarjetaDTO)
    assert resultado.id_resumen == "1097452662-2026-08-27"
    assert resultado.banco == "BBVA"
    assert resultado.tarjeta_tipo == "VISA"
    assert resultado.tarjeta_categoria == "GOLD"
    assert resultado.numero_cuenta == "1097452662"
    assert resultado.fecha_cierre == date(2026, 8, 27)
    assert resultado.fecha_vencimiento == date(2026, 9, 7)
    assert resultado.saldo_pesos == 144565.27
    assert resultado.saldo_dolares == 0.0
    assert resultado.pago_minimo == 82120.0
    assert len(resultado.consumos) == 1
    assert resultado.consumos[0].descripcion == "MIRGOR SACIFIA C.08/09 000014"

    assert len(repository.guardados) == 1
    assert repository.guardados[0].id_resumen == "1097452662-2026-08-27"
