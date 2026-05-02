# Arquitectura del Sistema — Link Seguro

## 1. Descripción general

Link Seguro es un sistema de detección de phishing aplicado a mensajes de Instagram. Recibe eventos en tiempo real desde la Meta Graph API a través de un webhook, extrae el texto de cada mensaje y lo somete a dos analizadores independientes (URLs y texto). El resultado es una clasificación de riesgo (`LOW`, `MEDIUM`, `HIGH`) que queda registrada en el logger estructurado del sistema.

El proyecto está construido sobre FastAPI y corre localmente expuesto a internet mediante ngrok durante el desarrollo.

---

## 2. Diagrama de arquitectura

```
┌─────────────────┐     HTTPS      ┌──────────────────┐     tunnel     ┌────────────┐
│ Usuario Instagram│──────────────▶│ Meta Graph API   │───────────────▶│   ngrok    │
└─────────────────┘                │ (v25.0 Webhooks) │                └─────┬──────┘
                                   └──────────────────┘                      │
                                                                              │ HTTP local
                                                                              ▼
                                                                   ┌──────────────────┐
                                                                   │  FastAPI          │
                                                                   │  POST /webhook    │
                                                                   │  GET  /webhook    │
                                                                   │  GET  /health     │
                                                                   └────────┬─────────┘
                                                                            │
                                                              ┌─────────────▼──────────────┐
                                                              │   PhishingOrchestrator      │
                                                              │  (análisis en paralelo)     │
                                                              └──────┬──────────┬───────────┘
                                                                     │          │
                                                           ┌─────────▼──┐  ┌───▼───────────┐
                                                           │URLAnalyzer │  │ TextAnalyzer  │
                                                           │(blacklist, │  │(regex patrones│
                                                           │shorteners, │  │ phishing ES/EN│
                                                           │keywords)   │  │               │
                                                           └─────────┬──┘  └───┬───────────┘
                                                                     │          │
                                                                     └────┬─────┘
                                                                          │
                                                                 ┌────────▼────────┐
                                                                 │  Logger          │
                                                                 │  (correlation ID,│
                                                                 │  stdout)         │
                                                                 └──────────────────┘
```

---

## 3. Descripción de cada capa

### Capa 1 — Ingesta (Webhook + Meta API)

**Archivo:** `app/webhook/router.py`

Expone dos endpoints bajo el prefijo `/webhook`:

- `GET /webhook`: Handshake de verificación con Meta. Compara el `hub.verify_token` recibido contra `META_VERIFY_TOKEN` de la configuración y devuelve `hub.challenge` si coincide.
- `POST /webhook`: Recibe el payload JSON de Meta, itera sobre `entry > messaging`, extrae `sender_id`, `text` e `is_echo`. Descarta ecos propios y mensajes sin texto.

### Capa 2 — Sanitización y privacidad

**Archivos:** `app/webhook/validator.py`, `app/utils/logger.py`

- `verify_signature()` implementa la validación HMAC-SHA256 del header `X-Hub-Signature-256` usando el `META_APP_SECRET`. Garantiza que el payload proviene de Meta. (Nota: está implementada pero pendiente de integración en el router.)
- El logger anonimiza el `sender_id` mostrando solo los últimos 4 caracteres: `sender=...XXXX`.

### Capa 3 — Motor de análisis

**Archivos:** `app/analysis/orchestrator.py`, `app/analysis/url_analyzer.py`, `app/analysis/text_analyzer.py`

`PhishingOrchestrator` lanza `URLAnalyzer` y `TextAnalyzer` en paralelo mediante `asyncio.gather` + `asyncio.to_thread`. Combina los puntajes con pesos configurables:

```
final_score = url_score × URL_WEIGHT + text_score × TEXT_WEIGHT
```

Valores por defecto: `URL_WEIGHT = 0.6`, `TEXT_WEIGHT = 0.4`.

**URLAnalyzer** evalúa cada URL encontrada con regex, sumando penalizaciones:

| Condición                        | Penalización |
|----------------------------------|-------------|
| Dominio en blacklist.txt         | +1.0        |
| Protocolo HTTP (no HTTPS)        | +0.3        |
| Servicio acortador de URLs       | +0.4        |
| Keyword sospechosa en la URL     | +0.2        |
| URL con más de 100 caracteres    | +0.2        |

El score final de URL es el máximo entre todas las URLs del mensaje, capped a 1.0.

**TextAnalyzer** aplica cuatro patrones regex con pesos:

| Patrón                  | Peso |
|-------------------------|------|
| `credential_request`    | 0.8  |
| `support_impersonation` | 0.6  |
| `urgency`               | 0.5  |
| `fraudulent_offer`      | 0.5  |

El score de texto es la suma de pesos de patrones encontrados, capped a 1.0.

### Capa 4 — Alertas y monitoreo

**Archivo:** `app/utils/logger.py`

Logger estructurado basado en `logging` estándar de Python. Cada línea incluye:

```
TIMESTAMP | LEVEL | CORRELATION_ID | MODULE | MENSAJE
```

El `correlation_id` es un UUID de 8 caracteres generado por request/contexto mediante `ContextVar`. Permite correlacionar logs de un mismo mensaje a través de todos los módulos.

---

## 4. Endpoints disponibles

| Método | Ruta       | Descripción                                                                 |
|--------|------------|-----------------------------------------------------------------------------|
| `GET`  | `/health`  | Health check. Devuelve `{"status": "running"}`.                             |
| `GET`  | `/webhook` | Verificación del webhook con Meta. Parámetros: `hub.mode`, `hub.verify_token`, `hub.challenge`. |
| `POST` | `/webhook` | Recepción de eventos de mensajería de Instagram. Body: payload JSON de Meta.|

---

## 5. Flujo de un mensaje desde que llega hasta que se registra

```
1. Meta envía POST /webhook con el payload JSON del mensaje
2. FastAPI recibe la request y la pasa al router
3. Router parsea el body y extrae entry > messaging[]
4. Para cada evento:
   a. Extrae sender_id, text, is_echo
   b. Si is_echo=True o text vacío → ignorar
   c. Logger registra "MENSAJE ENTRANTE: sender=...XXXX | texto=..."
   d. (TODO) Llama a PhishingOrchestrator.analyze({sender_id, text})
5. Orchestrator lanza en paralelo:
   a. URLAnalyzer.analyze(text) → URLResult(score, urls_found, reasons)
   b. TextAnalyzer.analyze(text) → TextResult(score, patterns_matched)
6. Calcula final_score = url_score × 0.6 + text_score × 0.4
7. Determina RiskLevel:
   - final_score >= 0.7 → HIGH
   - final_score >= 0.4 → MEDIUM
   - final_score <  0.4 → LOW
8. Logger registra "Analysis done | sender=... score=X.XX risk=LEVEL"
9. Router devuelve {"status": "ok"} a Meta
```

---

## 6. Decisiones arquitectónicas

**Separación por responsabilidad en módulos**
El proyecto divide webhook, analysis, models y utils en paquetes independientes. Esto permite reemplazar o extender cada capa sin afectar las demás.

**Análisis paralelo con `asyncio.gather` + `asyncio.to_thread`**
Los dos analizadores son independientes entre sí. Ejecutarlos en paralelo reduce la latencia total al tiempo del más lento, en lugar de la suma de ambos.

**Pesos y umbrales externalizados en configuración**
`URL_WEIGHT`, `TEXT_WEIGHT`, `RISK_THRESHOLD_HIGH` y `RISK_THRESHOLD_MEDIUM` se leen desde `.env` vía pydantic-settings. Esto permite ajustar la sensibilidad del sistema sin modificar código.

**Validación HMAC-SHA256 separada del router**
`verify_signature()` está en `validator.py` desacoplada del router, lo que facilita su testing unitario y su eventual integración como dependencia de FastAPI.

**Anonimización en logging**
El `sender_id` completo nunca se escribe en logs; solo los últimos 4 caracteres. Esto reduce la exposición de PII en caso de que los logs sean accedidos.

---

## 7. Limitaciones conocidas

- **Orchestrator no conectado:** el `POST /webhook` tiene un `# TODO: llamar al orchestrator`. El análisis existe pero no se invoca desde el endpoint aún.
- **HMAC no aplicado:** `verify_signature()` está implementada en `validator.py` pero no se llama en el router, por lo que cualquier payload puede llegar sin validar la firma.
- **Sin persistencia:** los resultados de análisis solo se registran en logs de stdout. No hay base de datos ni almacenamiento de históricos.
- **Tests vacíos:** el directorio `tests/` existe pero no contiene casos de prueba implementados.
- **Solo mensajes de texto:** el router ignora eventos que no tengan campo `text` (imágenes, stickers, reacciones).
- **Modo desarrollo:** la app de Meta solo puede recibir mensajes de usuarios añadidos como evaluadores mientras no esté en producción aprobada.
