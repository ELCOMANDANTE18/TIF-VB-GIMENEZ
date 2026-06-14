# Módulo: Motor de análisis

## Propósito

Coordina el pipeline de detección de phishing en cuatro etapas: análisis heurístico de URLs, análisis heurístico de texto, clasificación con IA generativa, y análisis holístico de conversación; combinando los resultados en un único nivel de riesgo (LOW / MEDIUM / HIGH).

## Archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `app/analysis/orchestrator.py` | Orquesta el pipeline completo y persiste el resultado |
| `app/analysis/url_analyzer.py` | Heurística de URLs: blacklist + patrones + URLhaus |
| `app/analysis/text_analyzer.py` | Heurística de texto: regex de patrones de ingeniería social |
| `app/analysis/conversation_observer.py` | Análisis holístico periódico del riesgo acumulado |

## Funciones principales

### `PhishingOrchestrator.analyze(message: dict) → AnalysisResult` — `orchestrator.py`

Función central del sistema. Recibe un diccionario con `sender_id`, `recipient_id`, `text`, `message_id`, `conversation_id` y ejecuta el pipeline completo.

**Pipeline paso a paso:**

```
1. get_conversation_info()          → estado previo (risk anterior, nro de mensajes)
2. URLAnalyzer.analyze() ──┐        → asyncio.gather (paralelo)
   TextAnalyzer.analyze() ─┘
3. Si url_score > 0.3: URLhaus API  → confirmar si la URL está activa
4. heuristic_score = URL×0.6 + Texto×0.4 → LOW/MEDIUM/HIGH por umbral
5. RAG retrieve()                   → contexto de base de conocimiento
6. groq_client.analyze_conversation() → clasificación IA (severity, MITRE, Cialdini…)
7. final_score = max(heuristic_score, ai_risk_score×ai_confidence)
8. save_analysis_result()           → SQLite
9. send_phishing_alert() [si HIGH]  → DM automático + email
10. conversation_observer.observe() → análisis holístico
```

**Retorna:** `AnalysisResult` con `risk_level`, `final_score`, `url_result`, `text_result`, campos IA.

### `URLAnalyzer.analyze(text: str) → URLResult` — `url_analyzer.py`

Extrae URLs con regex y puntúa cada una según señales acumulables:

| Señal | Score |
|-------|-------|
| Dominio en blacklist PhishTank (29.231) o `blacklist.txt` | +1.0 |
| URL con `http://` (sin TLS) | +0.3 |
| Acortador conocido (`bit.ly`, `cutt.ly`, `tinyurl.com`…) | +0.4 |
| Keyword sospechosa en URL (`login`, `verify`, `secure`…) | +0.2 |
| URL > 100 caracteres | +0.2 |

Devuelve el score máximo entre todas las URLs encontradas, con cap en 1.0.

### `URLAnalyzer.analyze_with_urlhaus(url: str) → dict` — async

Consulta la API de [URLhaus](https://urlhaus-api.abuse.ch/) para verificar si una URL está activa y confirmada maliciosa. Solo se llama si `url_score > 0.3`. Un hit `query_status == "is_online"` sube el score a ~1.0.

```python
# POST https://urlhaus-api.abuse.ch/v1/url/
# timeout: 3s, falla silenciosa
```

### `TextAnalyzer.analyze(text: str) → TextResult` — `text_analyzer.py`

Detecta patrones de ingeniería social con regex. Los patrones cubren español e inglés:

| Patrón | Regex detecta | Score |
|--------|--------------|-------|
| `credential_request` | "enviá tu contraseña", "share your pass", "give me your pin" | +0.8 |
| `support_impersonation` | "equipo de soporte", "Instagram support", "official", "verified" | +0.6 |
| `urgency` | "urgente", "24 horas", "suspended", "act now", "vence" | +0.5 |
| `fraudulent_offer` | "ganaste", "winner", "prize", "gratis", "gift card" | +0.5 |

El score total se acumula (múltiples patrones suman) con cap en 1.0. Los `patterns_matched` son la lista de nombres de patrones detectados, que el RAG usa para buscar contexto relevante.

### `should_trigger(total_mensajes, prev_risk, current_risk) → bool` — `conversation_observer.py`

Decide si el observador debe correr para esta conversación. Se dispara en:
- Mensajes 3, 5 y 10 (umbrales fijos)
- Cada 5 mensajes a partir del 10
- Cuando el riesgo escala (LOW→MEDIUM, LOW→HIGH, MEDIUM→HIGH)

### `observe(conversation_id, username, total_mensajes, prev_risk, current_risk)` — async

Toma los últimos 50 mensajes, arma un prompt especial indicando "evaluá el riesgo GLOBAL, no solo el último mensaje" y llama a UM Cloud AI. Persiste el resultado en `risk_level_conversacion` de la tabla `conversacion`.

## Flujo de datos

```
webhook → orchestrator.analyze()
               │
        ┌──────┴──────────────┐
        │                     │
   URLAnalyzer          TextAnalyzer
   (sync, thread)       (sync, thread)
        │                     │
        └──────┬──────────────┘
               │ url_score, text_score, reasons, patterns
               │
          [URLhaus si url_score > 0.3]
               │
          heuristic_score = URL×0.6 + Texto×0.4
               │
          RAG retrieve(text, reasons, patterns)
               │ retrieved_context
               ▼
          groq_client.analyze_conversation()  [ver 03-ai.md]
               │ severity, confidence, categoria, MITRE…
               │
          final_score = max(heuristic, ai×confidence)
               │
          save_analysis_result() → SQLite      [ver 04-db.md]
               │
          [HIGH] send_phishing_alert()         [ver 06-notifications.md]
               │
          conversation_observer.observe()
```

## Decisiones de diseño

**`asyncio.gather` + `asyncio.to_thread`**: `URLAnalyzer` y `TextAnalyzer` son síncronos (CPU-bound: regex, set lookups). Para correrlos en paralelo sin bloquear el event loop se usan `asyncio.to_thread`, que los ejecuta en el thread pool del executor de Python. La ganancia es pequeña (~50ms) pero correcta en diseño async.

**`max()` en lugar de promedio para combinar heurístico + IA**: si la heurística detecta una URL en PhishTank (score 1.0) pero la IA dice LOW, el sistema queda en HIGH. La IA puede escalar el riesgo pero nunca bajarlo. Decisión conservadora: un falso negativo (dejar pasar un ataque) es más costoso que un falso positivo. Ver `decisiones_tecnicas.md` #3.

**ConversationObserver separado del análisis de mensaje**: el orchestrator clasifica un mensaje puntual; el observer evalúa el riesgo acumulado de la sesión completa. Son tareas distintas con prompts distintos — compartir el resultado del primer análisis contaminaría la evaluación holística. Ver `decisiones_tecnicas.md` #7.

**Falla silenciosa del paso IA**: toda la sección de UM Cloud está envuelta en `try/except`. Si `UM_API_KEY` está vacío o la API falla, el sistema continúa con el resultado heurístico. El análisis nunca se interrumpe.

## Estado actual

- [x] URLAnalyzer con PhishTank (29.231 dominios) + `blacklist.txt`
- [x] URLAnalyzer con consulta async a URLhaus
- [x] TextAnalyzer con 4 patrones regex ES/EN
- [x] Pipeline paralelo URL + Text con `asyncio.gather`
- [x] Combinación heurístico + IA con `max()`
- [x] RAG activo (keyword matching, ver `03-ai.md`)
- [x] ConversationObserver con umbrales y detección de escalada
- [x] Falla silenciosa si UM Cloud no responde
- [ ] Más patrones en TextAnalyzer (actualmente solo 4 categorías)
- [ ] Tests unitarios por analizador (solo evaluación end-to-end disponible)
