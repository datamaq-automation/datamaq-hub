# Creación y verificación de la ficha de Google Business Profile

> **Ámbito:** Detalle del paso 1 del runbook de habilitación en
> [`gbp_ficha_google.md`](gbp_ficha_google.md) §4 — "Crear y verificar la ficha".
> **Última actualización:** 2026-09-02

---

## ⚠️ Aviso sobre la fuente

`gbp_ficha_google.md` cita como fuente de este paso el §11 de
`www-datamaq/docs/fase4_google_business_profile.md`. **Ese archivo no existe**:
no está en el working tree de `www-datamaq`, ni en su historial de git en
ninguna rama, ni en ninguna de las otras copias del repo presentes en esta
máquina. El plan de negocio de Fase 4 nunca fue redactado o commiteado.

Este documento reconstruye los datos necesarios desde dos fuentes que sí
existen y son citadas como autoritativas en otros documentos del repo
(`brand.yaml` para el NAP, `geografia.yaml` para las localidades), y desde
investigación del proceso actual de Google (septiembre 2026). **Los datos
marcados como "a validar" deben confirmarse con el dueño del negocio antes de
crear la ficha** — una vez verificada, cambiar nombre o dirección vía API es
causal de suspensión (ver `gbp_ficha_google.md` §5).

Si en algún momento aparece el plan de Fase 4 real (otra máquina, un Drive, una
rama no pusheada), sus datos priman sobre los de este documento.

---

## 1. Datos de la ficha

### 1.1 NAP (Nombre, Dirección, Teléfono)

Fuente: `www-datamaq/data/config/brand.yaml`, señalado como fuente de verdad
del NAP en `gbp_ficha_google.md` §5 y `specs/gbp_mcp.md`.

| Campo | Valor |
|---|---|
| Nombre | DataMaq |
| Dirección | Centenario 2795, Garín (1619), Buenos Aires, AR |
| Coordenadas | lat -34.4286681, lng -58.741936 |
| Email | info@datamaq.com.ar |
| Horario | Lu-Vi 08:00-18:00 |
| Teléfono | ⚠️ **A validar.** El YAML no tiene un teléfono fijo propio, solo WhatsApp `+54 11 5629 7160` (`data/seo/seo.yaml`). Decidir si ese es el número a publicar en la ficha o si hay que dar de alta una línea propia. |

### 1.2 Categoría primaria

**Servicio de ingeniería eléctrica** — este dato sí está atestiguado
textualmente en `gbp_ficha_google.md` §4 paso 1, no depende del plan faltante.

### 1.3 Tipo de negocio y área de servicio

**Service-area business, sin atención de clientes en el local** (dirección
oculta). Ver §2.2.

### 1.4 Localidades del área de servicio (candidatas, a validar)

⚠️ Fuente: `www-datamaq/data/meta/geografia.yaml` — es la lista de localidades
SEO del sitio web actual, **no necesariamente idéntica** al área de servicio
que definiría la ficha GBP. El propio archivo advierte: *"Solo localidades con
demanda industrial real dentro del areaServed declarado (Zona Norte GBA)"*.
Revalidar contra el radio de manejo real desde la base (Google recomienda no
superar ~2 horas):

1. Garín
2. Belén de Escobar
3. Tigre
4. Don Torcuato
5. El Talar
6. General Pacheco
7. Pilar
8. Parque Industrial Pilar
9. Campana
10. San Martín

### 1.5 Email propietario de la ficha

`agustin.deoz@gmail.com` — usar esta cuenta al crear/verificar la ficha y al
generar el `GBP_REFRESH_TOKEN` (ver `credenciales_entornos.md` §7, donde este
dato no estaba fijado a diferencia del email del MCC de Ads).

---

## 2. Procedimiento de creación

### 2.1 Alta de la ficha

1. Ir a [business.google.com](https://business.google.com) y entrar con
   `agustin.deoz@gmail.com`.
2. Buscar "DataMaq" para confirmar que no exista ya una ficha (evitar
   duplicados) — la búsqueda web del 2026-09-02 documentada en
   `gbp_ficha_google.md` §3 no encontró ninguna ficha pública.
3. "Añadir tu negocio a Google" → nombre: **DataMaq**.
4. Categoría: **Servicio de ingeniería eléctrica**.
5. Cuando pregunte si atienden clientes en la dirección del negocio, elegir
   **No** — esto configura el negocio como *service-area business*.

### 2.2 Configurar dirección oculta y área de servicio

1. Perfil → **Editar perfil** → **Ubicación** → junto a "Ubicación del
   negocio", **Editar**.
2. Desactivar **"Mostrar la dirección a los clientes"** → Guardar. La
   dirección real (Centenario 2795, Garín) queda registrada internamente
   para la verificación de Google, pero no se publica.
3. Cargar las áreas de servicio de §1.4 (hasta 20 permitidas por Google).
4. **No usar** apartado postal ni oficina virtual como dirección de
   verificación — Google lo detecta y es causal de suspensión.

### 2.3 Completar el perfil

- Teléfono (ver §1.1, a validar).
- Sitio web: el dominio de `www-datamaq`.
- Horario: Lu-Vi 08:00-18:00.
- Descripción del negocio y fotos — no cubierto por este documento, requiere
  input de marketing/negocio.

---

## 3. Verificación

Google ya no deja elegir el método: lo asigna según el rubro, la antigüedad de
la cuenta y cuánto puede confirmar el negocio por otras vías. Desde el **3 de
julio de 2026**, la mayoría de los negocios chicos son dirigidos a
verificación por **video** en lugar de postal.

### 3.1 Verificación por video (la más probable)

- Una sola toma continua, sin cortes, filmada con el celular.
- Debe mostrar: cartelería del negocio, el local o entorno de trabajo, y una
  acción de gestión en vivo (ej. mostrar documentación, herramientas,
  materiales del negocio).
- Revisión: hasta 5 días hábiles.

### 3.2 Otros métodos posibles (Google decide, no se eligen)

- **Postal**: código enviado por correo a la dirección real — 5 a 14 días de
  entrega más el tiempo de carga del código.
- **Teléfono/SMS**: código automático — reservado a negocios con huella
  digital pública ya establecida.
- **Email** o **Search Console**: instantáneo, poco frecuente para altas
  nuevas.

### 3.3 Si falla la verificación

Varios intentos fallidos llevan al estado **"No More Ways to Verify"** — un
callejón sin salida que exige contactar al soporte de Google y esperar varios
días hábiles antes de poder reintentar. Si esto ocurre, no seguir reintentando
por cuenta propia: abrir el caso de soporte primero.

---

## 4. Qué sigue después de verificar

Este documento cubre solo la creación y verificación de la ficha (paso 1 del
runbook). Los pasos siguientes —esperar 60 días, habilitar las 4 APIs,
solicitar Basic API Access, obtener el refresh token, resolver los
identificadores y verificar en vivo— están en
[`gbp_ficha_google.md`](gbp_ficha_google.md) §4, pasos 2 a 7. No se duplican
acá.

---

## 5. Fuentes

- [Manage your business address – Google Business Profile Help](https://support.google.com/business/answer/2853879)
- [Verify your business on Google – Google Business Profile Help](https://support.google.com/business/answer/7107242)
- [Google Business Profile Verification in 2026: New Warnings, Video Requirements & How to Stay Compliant](https://www.jxtgroup.com/google-business-profile-verification-in-2026-new-warnings-video-requirements-how-to-stay-compliant/)
- [Google Business Profile Verification Changes July 2026](https://wilsonalvarez.com/it-tech/google-business-profile-verification-overhaul-july-2026/)
- [How to Create a Google Business Profile: 11 Easy Steps](https://www.seo.com/blog/how-to-create-google-business-profile/)
