"""Pure domain services for deterministic salary calculation."""

from src.domain.liquidacion.entities import (
    ConceptoLiquidado,
    DesignacionDocente,
    LiquidacionCargoResultado,
    LiquidacionConsolidadaResultado,
)
from src.domain.liquidacion.exceptions import DesignacionInvalidaException
from src.domain.liquidacion.value_objects import (
    CodigoConceptoLiquidacion,
    DescripcionConceptoLiquidacion,
    EscalaAntiguedad,
    NivelCargo,
    ParametrosParitaria,
    SituacionRevista,
    TipoConceptoLiquidacion,
)

DIAS_MES_BASE: float = 30.0
FRACCION_SAC_MENSUAL: float = 1.0 / 12.0


class MotorLiquidacionDocenteService:
    """Deterministic calculation engine for DGCyE PBA teacher salaries."""

    def liquidar_cargo(
        self,
        designacion: DesignacionDocente,
        anios_antiguedad: int,
        paritaria: ParametrosParitaria,
        tope_bonif_restante: float | None = None,
    ) -> tuple[LiquidacionCargoResultado, float]:
        """Calculates a single position sequence deterministically.

        Returns the calculated cargo result and the updated remaining bonus quota.
        """
        if tope_bonif_restante is None:
            tope_bonif_restante = paritaria.tope_bonificaciones_modulos

        if designacion.carga_horaria <= 0:
            raise DesignacionInvalidaException(
                f"La carga horaria debe ser mayor a cero (recibido {designacion.carga_horaria})"
            )
        if (
            designacion.dias_trabajados < 0
            or designacion.dias_trabajados > DIAS_MES_BASE
        ):
            raise DesignacionInvalidaException(
                f"Días trabajados inválidos: {designacion.dias_trabajados}"
            )

        conceptos: list[ConceptoLiquidado] = []

        # 1. Básico
        if designacion.cargo_nivel == NivelCargo.SM:
            valor_modulo_basico = paritaria.basico_por_modulo_sm
        elif designacion.cargo_nivel == NivelCargo.PM:
            valor_modulo_basico = paritaria.basico_por_modulo_pm
        else:
            valor_modulo_basico = paritaria.basico_por_modulo_pm

        basico_mensual = valor_modulo_basico * designacion.carga_horaria
        basico_proporcional = round(
            (designacion.dias_trabajados / DIAS_MES_BASE) * basico_mensual, 2
        )

        if designacion.situacion_revista == SituacionRevista.PROVISIONAL:
            codigo_basico = CodigoConceptoLiquidacion.BASICO_PROVISIONAL
            desc_basico = DescripcionConceptoLiquidacion.BASICO_PROVISIONAL
        else:
            codigo_basico = CodigoConceptoLiquidacion.BASICO_SUPLENTE
            desc_basico = DescripcionConceptoLiquidacion.BASICO_SUPLENTE

        conceptos.append(
            ConceptoLiquidado(
                codigo=codigo_basico.value,
                descripcion=desc_basico.value,
                tipo=TipoConceptoLiquidacion.REMUNERATIVO,
                haberes=basico_proporcional,
            )
        )

        # 2. Antigüedad
        pct_antiguedad = EscalaAntiguedad.obtener_porcentaje(anios_antiguedad)
        monto_antiguedad = round(basico_proporcional * pct_antiguedad, 2)
        if monto_antiguedad > 0:
            conceptos.append(
                ConceptoLiquidado(
                    codigo=CodigoConceptoLiquidacion.ANTIGUEDAD.value,
                    descripcion=DescripcionConceptoLiquidacion.ANTIGUEDAD.value,
                    tipo=TipoConceptoLiquidacion.REMUNERATIVO,
                    haberes=monto_antiguedad,
                )
            )

        # 3. Bonificaciones Docentes (0455, 0667, 2575)
        nuevo_tope = tope_bonif_restante
        factor_dias = designacion.dias_trabajados / DIAS_MES_BASE

        if designacion.aplica_bonificaciones_plenas and tope_bonif_restante > 0:
            modulos_a_bonificar = min(designacion.carga_horaria, tope_bonif_restante)
            nuevo_tope = max(0.0, tope_bonif_restante - modulos_a_bonificar)

            if designacion.cargo_nivel == NivelCargo.SM:
                val_0455 = paritaria.bonif_0455_sm
                val_0667 = paritaria.bonif_0667_sm
                val_2575 = paritaria.bonif_2575_sm
            else:
                val_0455 = paritaria.bonif_0455_pm
                val_0667 = paritaria.bonif_0667_pm
                val_2575 = paritaria.bonif_2575_pm

            monto_0455 = round(val_0455 * modulos_a_bonificar * factor_dias, 2)
            monto_0667 = round(val_0667 * modulos_a_bonificar * factor_dias, 2)
            monto_2575 = round(val_2575 * modulos_a_bonificar * factor_dias, 2)

            if monto_0455 > 0:
                conceptos.append(
                    ConceptoLiquidado(
                        codigo=CodigoConceptoLiquidacion.BONIF_0455.value,
                        descripcion=DescripcionConceptoLiquidacion.BONIF_0455.value,
                        tipo=TipoConceptoLiquidacion.REMUNERATIVO,
                        haberes=monto_0455,
                    )
                )
            if monto_0667 > 0:
                conceptos.append(
                    ConceptoLiquidado(
                        codigo=CodigoConceptoLiquidacion.BONIF_0667.value,
                        descripcion=DescripcionConceptoLiquidacion.BONIF_0667.value,
                        tipo=TipoConceptoLiquidacion.REMUNERATIVO,
                        haberes=monto_0667,
                    )
                )
            if monto_2575 > 0:
                conceptos.append(
                    ConceptoLiquidado(
                        codigo=CodigoConceptoLiquidacion.BONIF_2575.value,
                        descripcion=DescripcionConceptoLiquidacion.BONIF_2575.value,
                        tipo=TipoConceptoLiquidacion.NO_REMUNERATIVO,
                        haberes=monto_2575,
                    )
                )

        # 4. SAC Proporcional en retroactivos o ceses de suplencia
        if designacion.es_retroactivo and designacion.dias_trabajados < DIAS_MES_BASE:
            remunerativo_base = basico_proporcional + monto_antiguedad
            monto_sac = round(remunerativo_base * FRACCION_SAC_MENSUAL, 2)
            if monto_sac > 0:
                conceptos.append(
                    ConceptoLiquidado(
                        codigo=CodigoConceptoLiquidacion.SAC.value,
                        descripcion=DescripcionConceptoLiquidacion.SAC.value,
                        tipo=TipoConceptoLiquidacion.REMUNERATIVO,
                        haberes=monto_sac,
                    )
                )

        # 5. Descuentos por Días de Paro
        if designacion.inasistencias_paro > 0:
            factor_paro = designacion.inasistencias_paro / DIAS_MES_BASE
            ret_basico = round(basico_proporcional * factor_paro, 2)
            ret_antig = round(monto_antiguedad * factor_paro, 2)

            conceptos.append(
                ConceptoLiquidado(
                    codigo=CodigoConceptoLiquidacion.RETENCION_BASICO_PARO.value,
                    descripcion=DescripcionConceptoLiquidacion.RETENCION_BASICO_PARO.value,
                    tipo=TipoConceptoLiquidacion.DESCUENTO,
                    descuentos=ret_basico,
                )
            )
            if ret_antig > 0:
                conceptos.append(
                    ConceptoLiquidado(
                        codigo=CodigoConceptoLiquidacion.RETENCION_ANTIG_PARO.value,
                        descripcion=DescripcionConceptoLiquidacion.RETENCION_ANTIG_PARO.value,
                        tipo=TipoConceptoLiquidacion.DESCUENTO,
                        descuentos=ret_antig,
                    )
                )

        # 6. Descuentos de Ley (IPS, IOMA)
        total_remunerativo = sum(
            c.haberes or 0.0
            for c in conceptos
            if c.tipo == TipoConceptoLiquidacion.REMUNERATIVO
        )

        desc_ips = round(total_remunerativo * paritaria.alicuota_ips, 2)
        desc_ioma = round(total_remunerativo * paritaria.alicuota_ioma, 2)

        conceptos.append(
            ConceptoLiquidado(
                codigo=CodigoConceptoLiquidacion.IPS.value,
                descripcion=DescripcionConceptoLiquidacion.IPS.value,
                tipo=TipoConceptoLiquidacion.DESCUENTO,
                descuentos=desc_ips,
            )
        )
        conceptos.append(
            ConceptoLiquidado(
                codigo=CodigoConceptoLiquidacion.IOMA.value,
                descripcion=DescripcionConceptoLiquidacion.IOMA.value,
                tipo=TipoConceptoLiquidacion.DESCUENTO,
                descuentos=desc_ioma,
            )
        )

        # 7. SUTEBA (sindicato + coseguro) si está adherido
        if designacion.aplica_suteba:
            suteba_sind = round(
                total_remunerativo * paritaria.alicuota_suteba_sindicato, 2
            )
            suteba_os = round(total_remunerativo * paritaria.alicuota_suteba_os, 2)
            conceptos.append(
                ConceptoLiquidado(
                    codigo=CodigoConceptoLiquidacion.SUTEBA_SINDICATO.value,
                    descripcion=DescripcionConceptoLiquidacion.SUTEBA_SINDICATO.value,
                    tipo=TipoConceptoLiquidacion.DESCUENTO,
                    descuentos=suteba_sind,
                )
            )
            conceptos.append(
                ConceptoLiquidado(
                    codigo=CodigoConceptoLiquidacion.SUTEBA_OBRA_SOCIAL.value,
                    descripcion=DescripcionConceptoLiquidacion.SUTEBA_OBRA_SOCIAL.value,
                    tipo=TipoConceptoLiquidacion.DESCUENTO,
                    descuentos=suteba_os,
                )
            )

        # Totales del cargo
        subtotal_haberes = round(sum(c.haberes or 0.0 for c in conceptos), 2)
        subtotal_descuentos = round(sum(c.descuentos or 0.0 for c in conceptos), 2)
        liquido = round(subtotal_haberes - subtotal_descuentos, 2)

        resultado = LiquidacionCargoResultado(
            secuencia=designacion.secuencia,
            escuela_codigo=designacion.escuela_codigo,
            escuela_nombre=designacion.escuela_nombre,
            cargo_nivel=designacion.cargo_nivel,
            carga_horaria=designacion.carga_horaria,
            situacion_revista=designacion.situacion_revista,
            periodo_liquidado=designacion.periodo_liquidado,
            dias_trabajados=designacion.dias_trabajados,
            es_retroactivo=designacion.es_retroactivo,
            conceptos=tuple(conceptos),
            subtotal_haberes=subtotal_haberes,
            subtotal_descuentos=subtotal_descuentos,
            liquido=liquido,
        )

        return resultado, nuevo_tope

    def liquidar_consolidado(
        self,
        designaciones: list[DesignacionDocente],
        anios_antiguedad: int,
        paritaria: ParametrosParitaria,
        periodo_proyectado: str | None = None,
        tope_bonificaciones_modulos: float | None = None,
    ) -> LiquidacionConsolidadaResultado:
        """Calculates a consolidated settlement for all designations of an agent."""
        if periodo_proyectado is None:
            periodo_proyectado = paritaria.periodo
        if tope_bonificaciones_modulos is None:
            tope_bonificaciones_modulos = paritaria.tope_bonificaciones_modulos

        # Ordenar designaciones: primero regulares (Superior, luego Media), luego retroactivos
        designaciones_ordenadas = sorted(
            designaciones,
            key=lambda d: (
                1 if d.es_retroactivo else 0,
                0 if d.cargo_nivel == NivelCargo.SM else 1,
                0 if d.situacion_revista == SituacionRevista.PROVISIONAL else 1,
                d.secuencia,
            ),
        )

        cargos_liquidados: list[LiquidacionCargoResultado] = []
        tope_restante = tope_bonificaciones_modulos

        for d in designaciones_ordenadas:
            res_cargo, tope_restante = self.liquidar_cargo(
                designacion=d,
                anios_antiguedad=anios_antiguedad,
                paritaria=paritaria,
                tope_bonif_restante=tope_restante,
            )
            cargos_liquidados.append(res_cargo)

        tot_remun = round(
            sum(
                sum(
                    c.haberes or 0.0
                    for c in cargo.conceptos
                    if c.tipo == TipoConceptoLiquidacion.REMUNERATIVO
                )
                for cargo in cargos_liquidados
            ),
            2,
        )
        tot_no_remun = round(
            sum(
                sum(
                    c.haberes or 0.0
                    for c in cargo.conceptos
                    if c.tipo == TipoConceptoLiquidacion.NO_REMUNERATIVO
                )
                for cargo in cargos_liquidados
            ),
            2,
        )
        tot_haberes = round(tot_remun + tot_no_remun, 2)
        tot_descuentos = round(
            sum(cargo.subtotal_descuentos for cargo in cargos_liquidados), 2
        )
        tot_liquido = round(tot_haberes - tot_descuentos, 2)

        tot_liquido_regular = round(
            sum(
                cargo.liquido for cargo in cargos_liquidados if not cargo.es_retroactivo
            ),
            2,
        )
        tot_liquido_retro = round(
            sum(cargo.liquido for cargo in cargos_liquidados if cargo.es_retroactivo), 2
        )

        return LiquidacionConsolidadaResultado(
            periodo_proyectado=periodo_proyectado,
            anios_antiguedad=anios_antiguedad,
            cargos_liquidados=tuple(cargos_liquidados),
            total_haberes_remunerativos=tot_remun,
            total_haberes_no_remunerativos=tot_no_remun,
            total_haberes=tot_haberes,
            total_descuentos=tot_descuentos,
            total_liquido=tot_liquido,
            total_liquido_regular=tot_liquido_regular,
            total_liquido_retroactivos=tot_liquido_retro,
        )
