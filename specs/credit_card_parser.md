# Especificación: Procesamiento y Consolidación de Tarjetas de Crédito

## 1. Objetivo y Contexto

Automatizar la ingesta y extracción de datos de resúmenes de tarjetas de crédito en formato PDF para los bancos operados por el usuario (BBVA y Banco Provincia). Esta funcionalidad permitirá consolidar los vencimientos, saldos en pesos/dólares y pagos mínimos, integrándolos en el Briefing Diario de finanzas personales.

**Problema:** El usuario recibe periódicamente resúmenes en PDF de múltiples tarjetas (Visa Gold, Mastercard Gold de BBVA, y Visa Classic de Banco Provincia). Para evitar olvidos y planificar los pagos, es necesario parsear de forma automatizada estos documentos y centralizar su información.

**Alcance:**
- Crear un parser genérico de tarjetas de crédito (`TarjetaCreditoParserPort`) y sus implementaciones concretas para BBVA (Visa/Mastercard) y BAPRO (Visa).
- Extraer metadatos clave: Entidad emisora, tipo de tarjeta, saldo actual en pesos, saldo actual en dólares, pago mínimo, fecha de cierre y fecha de vencimiento.
- Persistir la información consolidada en una nueva tabla en `leads.db`.
- Integrar las alertas de vencimientos de tarjetas en el caso de uso `ObtenerBriefingDiarioUseCase`.
- Crear el endpoint `POST /api/v1/tarjetas/cargar` para subir y procesar los PDFs.

---

## 2. Modelo de Dominio y Entidades

### 2.1 Entidad `ResumenTarjeta` (Dominio)
```python
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TransaccionTarjeta:
    fecha: date
    descripcion: str
    monto_pesos: float
    monto_dolares: float
    nro_cupon: str = ""


@dataclass(frozen=True)
class ResumenTarjeta:
    id_resumen: str
    banco: str  # e.g., "BBVA", "BAPRO"
    tarjeta_tipo: str  # e.g., "VISA", "MASTERCARD"
    tarjeta_categoria: str  # e.g., "GOLD", "CLASSIC"
    numero_cuenta: str
    fecha_cierre: date
    fecha_vencimiento: date
    saldo_pesos: float
    saldo_dolares: float
    pago_minimo: float
    consumos: tuple[TransaccionTarjeta, ...]
```

---

## 3. Arquitectura y Puertos

```
src/
├── domain/
│   └── tarjetas/
│       ├── entities.py         # ResumenTarjeta, TransaccionTarjeta
│       ├── ports.py            # TarjetaParserPort, TarjetaRepositoryPort
│       └── exceptions.py
├── application/
│   └── use_cases/
│       ├── procesar_resumen_tarjeta.py
│       └── obtener_briefing_diario.py (Modificado para incluir alertas)
└── adapters/
    ├── gateways/
    │   ├── sql_tarjeta_gateway.py
    │   └── pdf_tarjeta_parser_gateway.py
    └── controllers/
        └── tarjeta_controller.py
```

### 3.1 Base de Datos (Persistencia)
Se creará una nueva tabla en `leads.db`:
- `tarjeta_resumenes`: almacena metadatos del resumen.
- `tarjeta_consumos`: detalle de las transacciones individuales.

---

## 4. Matriz de Pruebas (RED Suite)

| ID | Escenario | PDF de Prueba | Verificación |
|---|---|---|---|
| TCP-1 | Parsear resumen BBVA Visa Gold | `20260829_visa.pdf` | Saldo: `$144.565,27`, Vto: `07-Sep-26`, Consumos: 1 |
| TCP-2 | Parsear resumen BBVA Mastercard Gold | `20260829_mastercard.pdf` | Saldo: `$22.547,36`, Vto: `07-Sep-26`, Consumos: 1 |
| TCP-3 | Parsear resumen BAPRO Visa Classic | `1151377322.01.27-08-26.pdf` | Saldo: `$277.449,24`, U$S: `55,78`, Vto: `07-Sep-26` |
