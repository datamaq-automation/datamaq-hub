"""Caso de uso para procesar resúmenes de tarjetas de crédito en PDF."""

import io

from src.application.dtos.tarjeta_dto import ResumenTarjetaDTO, TransaccionTarjetaDTO
from src.domain.tarjetas.entities import ResumenTarjeta
from src.domain.tarjetas.ports import TarjetaCreditoParserPort, TarjetaRepositoryPort


class ProcesarResumenTarjetaUseCase:
    """Orquesta el parseo de un PDF de tarjeta y su persistencia."""

    def __init__(
        self,
        parser: TarjetaCreditoParserPort,
        repository: TarjetaRepositoryPort,
    ) -> None:
        self._parser = parser
        self._repository = repository

    def execute(self, pdf_bytes: bytes) -> ResumenTarjetaDTO:
        """Parsea el PDF y persiste el resumen antes de mapearlo a DTO."""
        resumen = self._parser.parsear(io.BytesIO(pdf_bytes))
        self._repository.guardar(resumen)
        return self._to_dto(resumen)

    @staticmethod
    def _to_dto(resumen: ResumenTarjeta) -> ResumenTarjetaDTO:
        return ResumenTarjetaDTO(
            id_resumen=resumen.id_resumen,
            banco=resumen.banco,
            tarjeta_tipo=resumen.tarjeta_tipo,
            tarjeta_categoria=resumen.tarjeta_categoria,
            numero_cuenta=resumen.numero_cuenta,
            fecha_cierre=resumen.fecha_cierre,
            fecha_vencimiento=resumen.fecha_vencimiento,
            saldo_pesos=resumen.saldo_pesos,
            saldo_dolares=resumen.saldo_dolares,
            pago_minimo=resumen.pago_minimo,
            consumos=[
                TransaccionTarjetaDTO(
                    fecha=consumo.fecha,
                    descripcion=consumo.descripcion,
                    monto_pesos=consumo.monto_pesos,
                    monto_dolares=consumo.monto_dolares,
                    nro_cupon=consumo.nro_cupon,
                )
                for consumo in resumen.consumos
            ],
        )
