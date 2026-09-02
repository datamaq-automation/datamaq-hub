"""Gateway REST para las APIs de Google Business Profile (ficha de Maps).

Google no publica un SDK de Python para estas APIs y el repositorio no tiene
``google-api-python-client``, por lo que se usa el mismo patrón de ``urllib`` +
canje de ``refresh_token`` que ``gmail_api_gateway``. A diferencia de aquel, este
gateway nunca propaga excepciones: devuelve dicts con un discriminante ``status``,
que es la convención del resto de los gateways de analítica.

Superficie repartida en cuatro hosts:
  * ``mybusinessaccountmanagement``  → resolución de la cuenta
  * ``mybusinessbusinessinformation``→ datos de la ficha (categorías, área de servicio)
  * ``businessprofileperformance``   → métricas diarias y términos de búsqueda
  * ``mybusiness`` v4 (legacy)       → reseñas y publicaciones, sin reemplazo en v1
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, cast

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.domain.analytics.services import (
    FICHA_METRICA_CLICS_SITIO,
    FICHA_METRICA_CONVERSACIONES,
    FICHA_METRICA_INDICACIONES,
    FICHA_METRICA_LLAMADAS,
    FICHA_METRICAS_MAPS,
    FICHA_METRICAS_SEARCH,
)
from src.domain.cache.ports import ApiCachePort

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
API_ACCOUNT_MANAGEMENT = "https://mybusinessaccountmanagement.googleapis.com/v1"
API_BUSINESS_INFORMATION = "https://mybusinessbusinessinformation.googleapis.com/v1"
API_PERFORMANCE = "https://businessprofileperformance.googleapis.com/v1"
API_LEGACY_V4 = "https://mybusiness.googleapis.com/v4"

GBP_SCOPE = "https://www.googleapis.com/auth/business.manage"

# Todas las métricas diarias que expone la Business Profile Performance API y que
# tienen sentido para un service-area business B2B (se excluyen bookings y comida).
DAILY_METRICS: tuple[str, ...] = (
    *FICHA_METRICAS_MAPS,
    *FICHA_METRICAS_SEARCH,
    FICHA_METRICA_CLICS_SITIO,
    FICHA_METRICA_LLAMADAS,
    FICHA_METRICA_INDICACIONES,
    FICHA_METRICA_CONVERSACIONES,
)

# readMask exigido por la Business Information API: sin él la llamada falla.
LOCATION_READ_MASK = (
    "name,title,categories,storefrontAddress,phoneNumbers,websiteUri,"
    "regularHours,serviceArea,profile,metadata"
)

SETUP_GUIDE = (
    "Configurá GBP_CLIENT_ID, GBP_CLIENT_SECRET y GBP_REFRESH_TOKEN en .env. "
    "El refresh token se obtiene con: python scripts/authenticate_gmail_oauth.py "
    "--scopes gbp --email <propietario-de-la-ficha>"
)

APPROVAL_GUIDE = (
    "El proyecto de Google Cloud no tiene aprobado el Basic API Access de Business "
    "Profile (quota 0 QPM). Solicitalo con el 'GBP API contact form' desde un email "
    "propietario de la ficha y verificá la quota en console.cloud.google.com."
)


def _http_request(
    url: str,
    access_token: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """Ejecuta una petición autenticada y traduce los errores a dicts con ``status``."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            payload = cast(dict[str, Any], json.loads(raw)) if raw else {}
            return {"status": "success", "data": payload}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        # 429 con quota 0 QPM es la firma de un proyecto sin Basic API Access aprobado.
        if e.code == 429:
            return {
                "status": "api_not_approved",
                "code": e.code,
                "message": error_body,
                "setup_guide": APPROVAL_GUIDE,
            }
        if e.code in (401, 403):
            return {
                "status": "auth_error",
                "code": e.code,
                "message": error_body,
                "setup_guide": (
                    f"Verificá que el refresh token tenga el scope {GBP_SCOPE} y que la "
                    f"cuenta sea propietaria o administradora de la ficha. {APPROVAL_GUIDE}"
                ),
            }
        return {"status": "error", "code": e.code, "message": error_body}
    except (OSError, ValueError) as e:
        return {"status": "error", "message": str(e)}


class GoogleBusinessProfileGateway:
    """Encapsula las llamadas I/O a la ficha de Google Business Profile de DataMaq."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        account_id: str = "",
        location_id: str = "",
        cache: ApiCachePort | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.refresh_token = refresh_token.strip()
        self.account_id = account_id.strip()
        self.location_id = location_id.strip()
        self.timeout_seconds = timeout_seconds
        self._cache: ApiCachePort = cache if cache is not None else ApiCacheGateway()
        self._cached_token: str | None = None
        # Registro de claves escritas por este proceso, para poder invalidarlas
        # tras una escritura (``ApiCachePort`` no expone borrado).
        self._claves_cacheadas: set[str] = set()

    # ------------------------------------------------------------------ helpers

    @property
    def account_name(self) -> str:
        """Nombre de recurso de la cuenta, acepte o no el prefijo en la configuración."""
        if not self.account_id:
            return ""
        return (
            self.account_id
            if self.account_id.startswith("accounts/")
            else f"accounts/{self.account_id}"
        )

    @property
    def location_name(self) -> str:
        """Nombre de recurso de la ficha, acepte o no el prefijo en la configuración."""
        if not self.location_id:
            return ""
        return (
            self.location_id
            if self.location_id.startswith("locations/")
            else f"locations/{self.location_id}"
        )

    def _faltan_credenciales(self) -> dict[str, Any] | None:
        """Retorna el resultado degradado si falta alguna credencial OAuth."""
        if self.client_id and self.client_secret and self.refresh_token:
            return None
        return {
            "status": "missing_credentials",
            "message": "Credenciales OAuth2 de Google Business Profile incompletas.",
            "setup_guide": SETUP_GUIDE,
        }

    def _falta_ficha(self) -> dict[str, Any] | None:
        """Retorna el resultado degradado si faltan credenciales o la ficha a consultar.

        Las credenciales se reportan primero: sin ellas no hay forma de resolver
        la ficha, así que ``missing_location`` sería un diagnóstico engañoso.
        """
        faltan = self._faltan_credenciales()
        if faltan is not None:
            return faltan
        if self.location_name:
            return None
        return {
            "status": "missing_location",
            "message": "GBP_LOCATION_ID no está configurado.",
            "setup_guide": "Ejecutá get_gbp_status() para resolver la cuenta y la ficha disponibles.",
        }

    def _obtener_access_token(self) -> tuple[str | None, dict[str, Any] | None]:
        """Canjea el refresh token por un access token efímero."""
        if self._cached_token is not None:
            return self._cached_token, None

        payload = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            OAUTH_TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            return None, {
                "status": "auth_error",
                "code": e.code,
                "message": e.read().decode("utf-8", errors="ignore"),
                "setup_guide": SETUP_GUIDE,
            }
        except (OSError, ValueError) as e:
            return None, {"status": "error", "message": str(e)}

        token = body.get("access_token")
        if not token:
            return None, {
                "status": "auth_error",
                "message": "Respuesta OAuth2 sin access_token.",
                "setup_guide": SETUP_GUIDE,
            }

        self._cached_token = str(token)
        return self._cached_token, None

    def _guardar_en_cache(self, key: str, value: dict[str, Any]) -> None:
        """Cachea el resultado y registra la clave para poder invalidarla luego."""
        self._cache.set(key, value)
        self._claves_cacheadas.add(key)

    def _invalidar_prefijo(self, prefijo: str) -> None:
        """Expira las claves cacheadas por este proceso bajo un prefijo dado."""
        for key in sorted(k for k in self._claves_cacheadas if k.startswith(prefijo)):
            self._cache.set(key, None, ttl_seconds=0)
            self._claves_cacheadas.discard(key)

    def _pedir(
        self,
        url: str,
        method: str = "GET",
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resuelve credenciales y ejecuta la petición, degradando ante cualquier falla."""
        falta = self._faltan_credenciales()
        if falta is not None:
            return falta

        token, error = self._obtener_access_token()
        if token is None:
            return error if error is not None else {"status": "error"}

        return _http_request(
            url,
            token,
            method=method,
            body=body,
            timeout_seconds=self.timeout_seconds,
        )

    # ------------------------------------------------------------------ lectura

    def get_status(self) -> dict[str, Any]:
        """Reporta el estado de credenciales, la cuenta y la ficha configuradas."""
        falta = self._faltan_credenciales()
        if falta is not None:
            return falta

        cuentas = self._pedir(f"{API_ACCOUNT_MANAGEMENT}/accounts")
        if cuentas.get("status") != "success":
            return cuentas

        data = cast(dict[str, Any], cuentas.get("data", {}))
        disponibles = [
            {
                "name": str(a.get("name", "")),
                "accountName": str(a.get("accountName", "")),
                "type": str(a.get("type", "")),
            }
            for a in cast(list[dict[str, Any]], data.get("accounts", []))
        ]

        return {
            "status": "success",
            "scope_requerido": GBP_SCOPE,
            "account_configurada": self.account_name,
            "location_configurada": self.location_name,
            "cuentas_disponibles": disponibles,
            "listo_para_operar": bool(self.account_name and self.location_name),
        }

    def get_location_info(self) -> dict[str, Any]:
        """Obtiene categorías, área de servicio y datos de contacto de la ficha."""
        falta_ficha = self._falta_ficha()
        if falta_ficha is not None:
            return falta_ficha

        key = f"gbp:location_info:{self.location_name}"
        cached = self._cache.get(key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        campos = LOCATION_READ_MASK
        url = (
            f"{API_BUSINESS_INFORMATION}/{self.location_name}"
            f"?readMask={urllib.parse.quote(campos, safe=',')}"
        )
        result = self._pedir(url)
        if result.get("status") == "success":
            self._guardar_en_cache(key, result)
        return result

    def get_performance(self, days: int = 30) -> dict[str, Any]:
        """Consulta la serie diaria de impresiones, clics, llamadas e indicaciones.

        Consulta también el período inmediatamente anterior de la misma longitud,
        para que el dominio pueda calcular la variación sin una segunda llamada.
        """
        falta_ficha = self._falta_ficha()
        if falta_ficha is not None:
            return falta_ficha

        dias = max(1, min(540, days))
        key = f"gbp:performance:{self.location_name}:days_{dias}"
        cached = self._cache.get(key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        # La API entrega la serie con algunos días de retraso; se cierra en ayer.
        fin = _hoy_utc() - timedelta(days=1)
        inicio = fin - timedelta(days=dias - 1)
        inicio_previo = inicio - timedelta(days=dias)
        fin_previo = inicio - timedelta(days=1)

        actual = self._fetch_serie(inicio, fin)
        if actual.get("status") != "success":
            return actual

        previo = self._fetch_serie(inicio_previo, fin_previo)

        result: dict[str, Any] = {
            "status": "success",
            "location": self.location_name,
            "dias_analizados": dias,
            "rango": {"desde": inicio.isoformat(), "hasta": fin.isoformat()},
            "rango_previo": {
                "desde": inicio_previo.isoformat(),
                "hasta": fin_previo.isoformat(),
            },
            "metricas": actual.get("metricas", []),
            "metricas_periodo_previo": (
                previo.get("metricas", []) if previo.get("status") == "success" else []
            ),
        }
        self._guardar_en_cache(key, result)
        return result

    def _fetch_serie(self, desde: date, hasta: date) -> dict[str, Any]:
        """Trae y aplana la serie multi-métrica de un rango de fechas."""
        params: list[tuple[str, str]] = [
            ("dailyMetrics", metrica) for metrica in DAILY_METRICS
        ]
        params.extend(
            [
                ("dailyRange.start_date.year", str(desde.year)),
                ("dailyRange.start_date.month", str(desde.month)),
                ("dailyRange.start_date.day", str(desde.day)),
                ("dailyRange.end_date.year", str(hasta.year)),
                ("dailyRange.end_date.month", str(hasta.month)),
                ("dailyRange.end_date.day", str(hasta.day)),
            ]
        )
        url = (
            f"{API_PERFORMANCE}/{self.location_name}:fetchMultiDailyMetricsTimeSeries"
            f"?{urllib.parse.urlencode(params)}"
        )
        result = self._pedir(url)
        if result.get("status") != "success":
            return result

        data = cast(dict[str, Any], result.get("data", {}))
        metricas: list[dict[str, Any]] = []
        for multi in cast(
            list[dict[str, Any]], data.get("multiDailyMetricTimeSeries", [])
        ):
            for serie in cast(
                list[dict[str, Any]], multi.get("dailyMetricTimeSeries", [])
            ):
                nombre = str(serie.get("dailyMetric", ""))
                time_series = cast(dict[str, Any], serie.get("timeSeries", {}))
                for punto in cast(
                    list[dict[str, Any]], time_series.get("datedValues", [])
                ):
                    fecha = cast(dict[str, Any], punto.get("date", {}))
                    if not fecha:
                        continue
                    metricas.append(
                        {
                            "fecha": (
                                f"{int(fecha.get('year', 0)):04d}-"
                                f"{int(fecha.get('month', 0)):02d}-"
                                f"{int(fecha.get('day', 0)):02d}"
                            ),
                            "metrica": nombre,
                            # La API omite 'value' cuando el valor del día es 0.
                            "valor": int(punto.get("value", 0)),
                        }
                    )

        return {"status": "success", "metricas": metricas}

    def get_search_keywords(self, months: int = 1, limit: int = 25) -> dict[str, Any]:
        """Lista los términos con los que los usuarios encontraron la ficha."""
        falta_ficha = self._falta_ficha()
        if falta_ficha is not None:
            return falta_ficha

        meses = max(1, min(12, months))
        tope = max(1, min(100, limit))
        key = f"gbp:search_keywords:{self.location_name}:months_{meses}:limit_{tope}"
        cached = self._cache.get(key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        # La serie mensual se cierra en el mes anterior al corriente.
        hoy = _hoy_utc()
        mes_fin = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1)
        mes_inicio = mes_fin
        for _ in range(meses - 1):
            mes_inicio = (mes_inicio - timedelta(days=1)).replace(day=1)

        params = [
            ("monthlyRange.start_month.year", str(mes_inicio.year)),
            ("monthlyRange.start_month.month", str(mes_inicio.month)),
            ("monthlyRange.end_month.year", str(mes_fin.year)),
            ("monthlyRange.end_month.month", str(mes_fin.month)),
            ("pageSize", str(tope)),
        ]
        url = (
            f"{API_PERFORMANCE}/{self.location_name}/searchkeywords/impressions/monthly"
            f"?{urllib.parse.urlencode(params)}"
        )
        result = self._pedir(url)
        if result.get("status") != "success":
            return result

        data = cast(dict[str, Any], result.get("data", {}))
        terminos: list[dict[str, Any]] = []
        for fila in cast(list[dict[str, Any]], data.get("searchKeywordsCounts", [])):
            insights = cast(dict[str, Any], fila.get("insightsValue", {}))
            # Google entrega 'value' exacto o 'threshold' cuando el volumen es bajo.
            valor = insights.get("value", insights.get("threshold", 0))
            terminos.append(
                {
                    "termino": str(fila.get("searchKeyword", "")),
                    "impresiones": int(valor),
                    "es_umbral": "value" not in insights,
                }
            )

        payload: dict[str, Any] = {
            "status": "success",
            "location": self.location_name,
            "rango": {
                "desde": mes_inicio.strftime("%Y-%m"),
                "hasta": mes_fin.strftime("%Y-%m"),
            },
            "terminos": terminos,
        }
        self._guardar_en_cache(key, payload)
        return payload

    def get_reviews(self, limit: int = 20) -> dict[str, Any]:
        """Lista las reseñas de la ficha, marcando cuáles siguen sin respuesta."""
        falta_ficha = self._falta_ficha()
        if falta_ficha is not None:
            return falta_ficha
        if not self.account_name:
            return {
                "status": "missing_account",
                "message": "GBP_ACCOUNT_ID es obligatorio para leer reseñas (API v4).",
                "setup_guide": "Ejecutá get_gbp_status() para resolver la cuenta.",
            }

        tope = max(1, min(50, limit))
        key = f"gbp:reviews:{self.location_name}:limit_{tope}"
        cached = self._cache.get(key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        params = urllib.parse.urlencode(
            {"pageSize": str(tope), "orderBy": "updateTime desc"}
        )
        url = f"{API_LEGACY_V4}/{self._nombre_v4()}/reviews?{params}"
        result = self._pedir(url)
        if result.get("status") != "success":
            return result

        data = cast(dict[str, Any], result.get("data", {}))
        resenas: list[dict[str, Any]] = []
        for r in cast(list[dict[str, Any]], data.get("reviews", [])):
            reviewer = cast(dict[str, Any], r.get("reviewer", {}))
            reply = cast(dict[str, Any], r.get("reviewReply", {}))
            resenas.append(
                {
                    "review_id": str(r.get("reviewId", "")),
                    "autor": str(reviewer.get("displayName", "Anónimo")),
                    "estrellas": _estrellas_a_entero(str(r.get("starRating", ""))),
                    "comentario": str(r.get("comment", "")),
                    "fecha_utc": str(r.get("updateTime", r.get("createTime", ""))),
                    "tiene_respuesta": bool(reply.get("comment")),
                }
            )

        payload: dict[str, Any] = {
            "status": "success",
            "location": self.location_name,
            "rating_promedio": float(data.get("averageRating", 0.0)),
            "total_resenas": int(data.get("totalReviewCount", len(resenas))),
            "resenas": resenas,
        }
        self._guardar_en_cache(key, payload)
        return payload

    # ---------------------------------------------------------------- escritura

    def create_post(
        self,
        summary: str,
        cta_url: str,
        cta_type: str = "LEARN_MORE",
        schedule_time: str | None = None,
    ) -> dict[str, Any]:
        """Crea una publicación en la ficha, opcionalmente programada a futuro.

        No valida el contenido: eso es responsabilidad del guardrail de dominio,
        que corre antes en ``PublicarEnFichaGoogleUseCase``.
        """
        falta_ficha = self._falta_ficha()
        if falta_ficha is not None:
            return falta_ficha
        if not self.account_name:
            return {
                "status": "missing_account",
                "message": "GBP_ACCOUNT_ID es obligatorio para publicar (API v4).",
                "setup_guide": "Ejecutá get_gbp_status() para resolver la cuenta.",
            }

        body: dict[str, Any] = {
            "languageCode": "es-419",
            "summary": summary,
            "topicType": "STANDARD",
            "callToAction": {"actionType": cta_type, "url": cta_url},
        }
        if schedule_time is not None:
            body["scheduledTime"] = schedule_time

        url = f"{API_LEGACY_V4}/{self._nombre_v4()}/localPosts"
        result = self._pedir(url, method="POST", body=body)
        if result.get("status") != "success":
            return result

        data = cast(dict[str, Any], result.get("data", {}))
        return {
            "status": "success",
            "post_name": str(data.get("name", "")),
            "state": str(data.get("state", "")),
            "search_url": str(data.get("searchUrl", "")),
            "scheduled_time": str(data.get("scheduledTime", "")),
        }

    def reply_to_review(
        self, review_id: str, comment: str, overwrite: bool = False
    ) -> dict[str, Any]:
        """Publica o reemplaza la respuesta del negocio a una reseña.

        El chequeo de sobrescritura vive en el guardrail de dominio; acá
        ``overwrite`` sólo documenta la intención en la respuesta.
        """
        falta_ficha = self._falta_ficha()
        if falta_ficha is not None:
            return falta_ficha
        if not self.account_name:
            return {
                "status": "missing_account",
                "message": "GBP_ACCOUNT_ID es obligatorio para responder reseñas (API v4).",
                "setup_guide": "Ejecutá get_gbp_status() para resolver la cuenta.",
            }

        url = f"{API_LEGACY_V4}/{self._nombre_v4()}/reviews/{review_id}/reply"
        result = self._pedir(url, method="PUT", body={"comment": comment})
        if result.get("status") != "success":
            return result

        # La respuesta cambia el estado de las reseñas cacheadas.
        self._invalidar_prefijo(f"gbp:reviews:{self.location_name}")

        data = cast(dict[str, Any], result.get("data", {}))
        return {
            "status": "success",
            "review_id": review_id,
            "sobrescribio_respuesta_previa": overwrite,
            "comment": str(data.get("comment", comment)),
            "update_time": str(data.get("updateTime", "")),
        }

    def _nombre_v4(self) -> str:
        """Construye el nombre de recurso ``accounts/X/locations/Y`` que exige la API v4."""
        return f"{self.account_name}/{self.location_name}"


def _hoy_utc() -> date:
    """Fecha actual en UTC; la API entrega la serie con retraso, así que el huso no discrimina."""
    return datetime.now(timezone.utc).date()


def _estrellas_a_entero(star_rating: str) -> int:
    """Traduce el enum StarRating de la API v4 a un entero de 1 a 5."""
    mapa = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
    return mapa.get(star_rating.strip().upper(), 0)
