# Runbook: Credenciales y Variables de Entorno por Entorno

> **Ámbito:** Sincronización de `.env` entre el entorno local de desarrollo y el
> VPS DonWeb de producción (`/var/www/datamaq-hub/`).
> **Relacionado:** [`vps_replica_runbook.md`](vps_replica_runbook.md) (datos),
> [`analytics_and_ads.md`](analytics_and_ads.md) (topología de cuentas Google).

---

## 1. Principio: sincronizar secretos, NO rutas

Las 13 claves del `.env` se dividen en dos categorías, y confundirlas es la causa
raíz de la caída silenciosa de GA4 documentada en la Sección 4.

| Categoría | Claves | Regla |
|---|---|---|
| **Secretos compartidos** (12) | `CLARITY_ID`, `CLARITY_API_TOKEN`, `GA4_PROPERTY_ID`, `GOOGLE_ADS_*` (5), `DEEPSEEK_API_KEY`, `MAIL_ACCOUNTS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | **Idénticas** en local y VPS. Si divergen, es drift. |
| **Rutas de filesystem** (1) | `GOOGLE_APPLICATION_CREDENTIALS` | **Deben diferir.** Apuntan a un archivo distinto en cada máquina. |

Valores vigentes de la ruta:

```ini
# Local
GOOGLE_APPLICATION_CREDENTIALS=/home/agustin/.config/gcp/datamaq-ga4-key.json
# VPS DonWeb
GOOGLE_APPLICATION_CREDENTIALS=/etc/datamaq-hub/ga4-key.json
```

### Por qué en el VPS la credencial vive en `/etc/datamaq-hub/`

**No debe colocarse dentro del working tree del repo.** `scripts/deploy.sh:19`
ejecuta:

```bash
git clean -df -e .venv/ -e data/
```

Eso elimina cualquier archivo o directorio no rastreado que no esté en la lista de
exclusiones — un `secrets/` dentro del proyecto se borraría en el próximo despliegue
y GA4 volvería a caer. `/etc/datamaq-hub/` queda fuera del alcance de `git clean`.

Permisos correctos en el VPS (el servicio corre como `User=datamaq`):

```bash
install -d -o datamaq -g datamaq -m 750 /etc/datamaq-hub
chown datamaq:datamaq /etc/datamaq-hub/ga4-key.json
chmod 600 /etc/datamaq-hub/ga4-key.json
```

---

## 2. Auditar el drift entre entornos

Compara clave por clave **sin exponer los secretos**, usando un hash truncado de
cada valor. Ejecutar desde la máquina local:

```bash
hash_env() {
  while IFS= read -r l; do
    case "$l" in \#*|"") continue;; esac
    k="${l%%=*}"; v="${l#*=}"
    printf "%s %s\n" "$k" "$(printf %s "$v" | sha256sum | cut -c1-10)"
  done | sort
}

diff <(hash_env < .env) \
     <(ssh vps 'cat /var/www/datamaq-hub/.env' | hash_env)
```

**Resultado esperado:** una única diferencia, la de
`GOOGLE_APPLICATION_CREDENTIALS`. Cualquier otra línea es drift a corregir.

> El servicio systemd carga las variables vía
> `EnvironmentFile=/var/www/datamaq-hub/.env`, sin directivas `Environment=`
> adicionales. Ese archivo es la única fuente de configuración en producción.

---

## 3. Regenerar el `GOOGLE_ADS_REFRESH_TOKEN` (requiere navegador)

**Síntoma:** los endpoints `/analytics/ads/*` y `/analytics/summary` devuelven
HTTP 500 con `invalid_grant: Token has been expired or revoked.`

Un refresh token de Google se revoca por inactividad prolongada, cambio de
contraseña de la cuenta, o revocación manual en la consola de seguridad. **El
token es el mismo en local y en el VPS**, así que la caída afecta a ambos
entornos y la corrección debe aplicarse en los dos.

### Paso 1 — Autorizar (en la máquina local, con navegador)

El VPS no tiene navegador y el redirect URI apunta a `localhost`, por lo que este
paso **no puede ejecutarse por SSH**.

```bash
./venv/bin/python scripts/authenticate_gmail_oauth.py \
    --scopes ads \
    --email agustin.deoz@gmail.com
```

El flag `--scopes ads` solicita `https://www.googleapis.com/auth/adwords` en lugar
de los scopes de Gmail. El script abre (o copia al portapapeles) la URL de
autorización, levanta un servidor local en el puerto 8080 para recibir el
callback, e imprime el `refresh_token` resultante.

> **Cuenta a usar:** la que tiene acceso al MCC `405-777-8237`
> (ver matriz de permisos en `analytics_and_ads.md`, Sección 1).
>
> **Si falla con `redirect_uri_mismatch`:** el URI registrado en GCP no coincide.
> Probar `--variant localhost` (sin barra final) o `--variant ip_slash`, o pasar el
> valor exacto con `--redirect-uri`.

### Paso 2 — Escribir el token en ambos entornos

Sustituir `NUEVO_TOKEN` por el valor obtenido:

```bash
# Local
sed -i "s|^GOOGLE_ADS_REFRESH_TOKEN=.*|GOOGLE_ADS_REFRESH_TOKEN=NUEVO_TOKEN|" .env

# VPS (con backup previo)
ssh vps 'cd /var/www/datamaq-hub && cp -a .env .env.bak.$(date +%Y%m%d_%H%M%S) && \
  sed -i "s|^GOOGLE_ADS_REFRESH_TOKEN=.*|GOOGLE_ADS_REFRESH_TOKEN=NUEVO_TOKEN|" .env'
```

### Paso 3 — Reiniciar y verificar

```bash
ssh vps 'systemctl restart datamaq-hub.service'
sleep 10   # los workers tardan ~8s en aceptar conexiones
ssh vps 'curl -s http://127.0.0.1:8013/api/v1/analytics/ads/campaigns | head -c 300'
```

Debe responder `"success":true` sin `invalid_grant`.

### Paso 4 — Confirmar que no quedó drift

Re-ejecutar la auditoría de la Sección 2: la única diferencia debe seguir siendo
`GOOGLE_APPLICATION_CREDENTIALS`.

---

## 4. Reponer la credencial de GA4 (Service Account)

**Síntoma:** `/analytics/ga4/conversions` devuelve **HTTP 200** con
`{"status":"missing_credentials"}`. Es un fallo silencioso: el código de estado es
200, así que un healthcheck que solo mire HTTP no lo detecta.

La guarda en `src/adapters/gateways/ga4_gateway.py:25-34` es una disyunción de tres
condiciones que comparten un único mensaje de error:

```python
if (not ga4_property_id
    or not google_application_credentials
    or not os.path.exists(google_application_credentials)):
```

Por eso el mensaje —"GA4_PROPERTY_ID o GOOGLE_APPLICATION_CREDENTIALS no están
configurados válidamente"— **no indica cuál de las tres falló**. Diagnosticar antes
de actuar, porque el arreglo es distinto en cada caso:

```bash
ssh vps 'cd /var/www/datamaq-hub && \
  grep -E "^(GA4_PROPERTY_ID|GOOGLE_APPLICATION_CREDENTIALS)=" .env && \
  p=$(grep "^GOOGLE_APPLICATION_CREDENTIALS=" .env | cut -d= -f2-) && \
  ls -la "$p" 2>&1'
```

- **Falta `GA4_PROPERTY_ID`** → copiar el valor desde el `.env` local (es un secreto
  compartido, debe ser idéntico).
- **Falta `GOOGLE_APPLICATION_CREDENTIALS`** → definir la ruta del entorno (Sección 1).
- **La ruta existe pero el archivo no** → es el caso habitual, resuelto abajo. **No
  hace falta crear una cuenta de servicio nueva en GCP**: la que ya existe
  (`ga4-analytics-reader@datamaq-505320.iam.gserviceaccount.com`) sigue siendo
  válida; solo falta el JSON en el disco del VPS.

### Copiar la credencial existente al VPS

```bash
ssh vps 'install -d -o datamaq -g datamaq -m 750 /etc/datamaq-hub'
scp /home/agustin/.config/gcp/datamaq-ga4-key.json vps:/etc/datamaq-hub/ga4-key.json
ssh vps 'chown datamaq:datamaq /etc/datamaq-hub/ga4-key.json && \
         chmod 600 /etc/datamaq-hub/ga4-key.json'
ssh vps 'cd /var/www/datamaq-hub && cp -a .env .env.bak.$(date +%Y%m%d_%H%M%S) && \
  sed -i "s|^GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=/etc/datamaq-hub/ga4-key.json|" .env'
ssh vps 'systemctl restart datamaq-hub.service'
```

Verificar (esperar ~10s a que levanten los workers):

```bash
ssh vps 'curl -s http://127.0.0.1:8013/api/v1/analytics/ga4/conversions | head -c 300'
```

Debe devolver `"status":"success"` con `total_rows` mayor a cero.

> Si en cambio devuelve un error de permisos de la API, el service account perdió
> el rol de lectura sobre la propiedad GA4 `533265197`: reagregarlo como *Viewer*
> en la administración de GA4. Ese caso sí requiere pasar por la consola de Google.

---

## 5. Verificación integral de los tres proveedores

```bash
for e in /api/v1/analytics/ga4/conversions \
         /api/v1/analytics/clarity/live \
         /api/v1/analytics/ads/campaigns \
         /api/v1/analytics/summary; do
  printf "%-45s " "$e"
  ssh vps "curl -s -o /tmp/r -w '%{http_code}' 'http://127.0.0.1:8013$e'; \
           python3 -c \"import json;print(' ',json.load(open('/tmp/r')).get('data',{}).get('status','-'))\" 2>/dev/null || echo"
done
```

Estado sano: los cuatro en HTTP 200, ninguno con `missing_credentials`.

**Atención al fallo silencioso:** GA4 y Google Ads devuelven `200 OK` con
`status: missing_credentials` cuando les faltan credenciales. Un monitor que solo
verifique el código HTTP los reporta como sanos. Verificar siempre el campo
`status` del cuerpo, no solo el código de respuesta.

---

## 6. Cobertura de tipos de `scripts/`

`pyrightconfig.json` declara `include: ["src", "scripts"]`. Hasta el 2026-09-01
declaraba solo `["src"]`, de modo que `scripts/ci.sh` (`pyright src/`) y
`scripts/pre-push.sh` (`pyright` sin argumentos) dejaban `scripts/` sin verificar,
mientras Pylance sí analizaba cualquier archivo abierto en el editor. Esa asimetría
mantuvo 8 diagnósticos sin detectar, incluido un `import urllib.error` faltante en
la ruta de alertas de `analytics_watchdog.py`.

Al tocar cualquier script, verificar con:

```bash
pyright scripts/          # debe dar 0 errores
./scripts/pre-push.sh     # gate completo
```

> El `setup_guide` de `ga4_gateway.py:33` remitía a *"analytics_and_ads.md Sección
> 4"* (que trata sobre Servidores FastMCP & Watchdog) para configurar la cuenta de
> servicio. Corregido: ahora apunta a la Sección 4 de este runbook y a la Sección 2
> de `analytics_and_ads.md`, que es donde está el mapa de variables.
