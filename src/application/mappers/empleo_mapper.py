"""Mappers for empleo bounded context."""

from src.application.dtos.empleo_dtos import (
    InteraccionDTO,
    OfertaLaboralDTO,
    OportunidadDTO,
    PerfilProfesionalDTO,
    RegistrarInteraccionDTO,
    RegistrarOportunidadDTO,
    ResultadoBusquedaDTO,
)
from src.domain.empleo.entities import (
    InteraccionPostulacion,
    OfertaLaboral,
    OportunidadLaboral,
    PerfilProfesional,
    ResultadoBusquedaEmpleo,
)
from src.domain.empleo.value_objects import EstadoOportunidad, ModalidadTrabajo


class EmpleoMapper:
    """Mapeador bidireccional entre entidades de dominio y DTOs."""

    @staticmethod
    def perfil_dto_a_entidad(dto: PerfilProfesionalDTO) -> PerfilProfesional:
        modalidades: list[ModalidadTrabajo] = []
        for m in dto.modalidades_admitidas:
            try:
                modalidades.append(ModalidadTrabajo(m.upper()))
            except ValueError:
                pass

        return PerfilProfesional(
            titulo_deseado=dto.titulo_deseado,
            palabras_clave_prioritarias=tuple(dto.palabras_clave_prioritarias),
            palabras_clave_secundarias=tuple(dto.palabras_clave_secundarias),
            ubicaciones_preferidas=tuple(dto.ubicaciones_preferidas),
            modalidades_admitidas=tuple(modalidades),
        )

    @staticmethod
    def oferta_entidad_a_dto(entidad: OfertaLaboral) -> OfertaLaboralDTO:
        return OfertaLaboralDTO(
            id_oferta=entidad.id_oferta,
            titulo=entidad.titulo,
            empresa=entidad.empresa,
            ubicacion=entidad.ubicacion,
            descripcion=entidad.descripcion,
            url_postulacion=entidad.url_postulacion,
            fecha_publicacion=entidad.fecha_publicacion,
            fuente=entidad.fuente.value,
            modalidad=entidad.modalidad.value,
            tags=list(entidad.tags),
            score_afinidad=entidad.score_afinidad,
            nivel_afinidad=entidad.nivel_afinidad.value,
            requisitos=list(entidad.requisitos),
        )

    @staticmethod
    def resultado_entidad_a_dto(
        entidad: ResultadoBusquedaEmpleo,
    ) -> ResultadoBusquedaDTO:
        return ResultadoBusquedaDTO(
            ofertas=[EmpleoMapper.oferta_entidad_a_dto(o) for o in entidad.ofertas],
            total_encontradas=entidad.total_encontradas,
            fuentes_consultadas=[f.value for f in entidad.fuentes_consultadas],
            fecha_consulta=entidad.fecha_consulta,
        )

    @staticmethod
    def oportunidad_entidad_a_dto(entidad: OportunidadLaboral) -> OportunidadDTO:
        return OportunidadDTO(
            id=entidad.id,
            titulo=entidad.titulo,
            empresa=entidad.empresa,
            consultora=entidad.consultora,
            ubicacion=entidad.ubicacion,
            regimen=entidad.regimen,
            jornada=entidad.jornada,
            salario_min=entidad.salario_min,
            salario_max=entidad.salario_max,
            salario_moneda=entidad.salario_moneda,
            salario_bruto_neto=entidad.salario_bruto_neto,
            url_fuente=entidad.url_fuente,
            estado=entidad.estado.value
            if isinstance(entidad.estado, EstadoOportunidad)
            else str(entidad.estado),
            fecha_publicacion=entidad.fecha_publicacion,
            fecha_postulacion=entidad.fecha_postulacion,
            fecha_entrevista=entidad.fecha_entrevista,
            fecha_oferta=entidad.fecha_oferta,
            fecha_descarte=entidad.fecha_descarte,
            fecha_congelacion=entidad.fecha_congelacion,
            notas=entidad.notas,
            requisitos=list(entidad.requisitos),
            origen=entidad.origen,
            tipo_modalidad=entidad.tipo_modalidad,
            canal_adquisicion=entidad.canal_adquisicion,
            id_campania=entidad.id_campania,
        )

    @staticmethod
    def oportunidad_dto_a_entidad(
        dto: RegistrarOportunidadDTO | OportunidadDTO,
    ) -> OportunidadLaboral:
        try:
            estado = EstadoOportunidad(dto.estado.upper())
        except (ValueError, AttributeError):
            estado = EstadoOportunidad.DETECTADA

        op_id = getattr(dto, "id", None)
        return OportunidadLaboral(
            id=op_id,
            titulo=dto.titulo,
            empresa=dto.empresa,
            consultora=dto.consultora,
            ubicacion=dto.ubicacion,
            regimen=dto.regimen,
            jornada=dto.jornada,
            salario_min=dto.salario_min,
            salario_max=dto.salario_max,
            salario_moneda=dto.salario_moneda,
            salario_bruto_neto=dto.salario_bruto_neto,
            url_fuente=dto.url_fuente,
            estado=estado,
            fecha_publicacion=dto.fecha_publicacion,
            fecha_postulacion=dto.fecha_postulacion,
            fecha_entrevista=dto.fecha_entrevista,
            fecha_oferta=dto.fecha_oferta,
            fecha_descarte=dto.fecha_descarte,
            fecha_congelacion=dto.fecha_congelacion,
            notas=dto.notas,
            requisitos=tuple(dto.requisitos),
            origen=dto.origen,
            tipo_modalidad=dto.tipo_modalidad,
            canal_adquisicion=dto.canal_adquisicion,
            id_campania=dto.id_campania,
        )

    @staticmethod
    def interaccion_entidad_a_dto(
        entidad: InteraccionPostulacion,
    ) -> InteraccionDTO:
        return InteraccionDTO(
            id=entidad.id,
            oportunidad_id=entidad.oportunidad_id,
            fecha=entidad.fecha,
            canal=entidad.canal,
            contacto_nombre=entidad.contacto_nombre,
            contacto_email=entidad.contacto_email,
            contacto_telefono=entidad.contacto_telefono,
            contacto_empresa=entidad.contacto_empresa,
            resumen=entidad.resumen,
            proxima_accion=entidad.proxima_accion,
            fecha_proxima_accion=entidad.fecha_proxima_accion,
        )

    @staticmethod
    def interaccion_dto_a_entidad(
        dto: RegistrarInteraccionDTO | InteraccionDTO,
    ) -> InteraccionPostulacion:
        interaccion_id = getattr(dto, "id", None)
        return InteraccionPostulacion(
            id=interaccion_id,
            oportunidad_id=dto.oportunidad_id,
            fecha=dto.fecha,
            canal=dto.canal,
            contacto_nombre=dto.contacto_nombre,
            contacto_email=dto.contacto_email,
            contacto_telefono=dto.contacto_telefono,
            contacto_empresa=dto.contacto_empresa,
            resumen=dto.resumen,
            proxima_accion=dto.proxima_accion,
            fecha_proxima_accion=dto.fecha_proxima_accion,
        )
