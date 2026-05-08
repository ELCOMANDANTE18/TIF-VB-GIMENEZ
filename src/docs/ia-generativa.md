# IA Generativa — Groq + LLaMA 3.3 70B

## 1. Modelo utilizado

| Parámetro | Valor |
|---|---|
| Proveedor | Groq |
| Modelo | `llama-3.3-70b-versatile` |
| Temperature | `0.1` |
| Max tokens | `512` |
| Timeout | `10.0` segundos |
| Cliente | `groq.AsyncGroq` (asincrónico) |

El modelo se invoca desde `app/ai/groq_client.py` usando el SDK oficial `groq==1.2.0`.

---

## 2. Por qué análisis contextual vs mensaje aislado

El sistema no analiza cada mensaje de forma aislada. En cambio, recupera los **últimos 10 mensajes** de la conversación desde Supabase antes de llamar al modelo.

**Motivación**: muchos ataques de ingeniería social son graduales. Un atacante puede iniciar con una conversación amigable y luego, varios mensajes después, pedir credenciales o enviar un link malicioso. Analizar solo el último mensaje produciría un falso negativo en los mensajes iniciales del ataque y podría no capturar el patrón completo.

El system prompt explica esto explícitamente:

> *"Considerá el historial completo para detectar patrones que en un solo mensaje no serían evidentes. Por ejemplo: conversación que empieza amigable y luego pide credenciales o datos personales."*

**Contrabalance importante**: el prompt también indica que un mensaje inocente (saludo, respuesta corta) que aparezca **después** de mensajes sospechosos no debe clasificarse como phishing. El análisis es sobre el mensaje **actual**, usando el historial como **contexto**, no como condena.

---

## 3. System prompt completo

Archivo: `app/ai/prompts.py`

```
Sos un analista experto en ciberseguridad especializado en
detección de phishing e ingeniería social en redes sociales.

Tu tarea es analizar una conversación de Instagram DMs y determinar
si hay intentos de phishing, estafa o ingeniería social.

Considerá el historial completo para detectar patrones que en un
solo mensaje no serían evidentes. Por ejemplo: conversación que
empieza amigable y luego pide credenciales o datos personales.

Respondé ÚNICAMENTE con un JSON válido con esta estructura exacta:
{
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "confidence": 0.0 a 1.0,
  "explanation": "explicación en español en lenguaje simple, máximo 2 oraciones",
  "recommendation": "recomendación concreta para el usuario, máximo 1 oración",
  "patterns_detected": ["lista de patrones detectados, puede estar vacía"]
}

No agregues texto fuera del JSON. No uses markdown. Solo el JSON.

IMPORTANTE:
- Analizá si el MENSAJE ACTUAL contiene phishing, no los anteriores.
- El historial es contexto para detectar PATRONES en curso.
- Un mensaje inocente después de uno sospechoso NO es phishing.
- Solo marcá HIGH si el mensaje actual contiene: links maliciosos,
  solicitud de credenciales, urgencia falsa o suplantación de identidad.
- Mensajes de conversación normal como saludos o palabras sueltas
  son siempre LOW aunque el historial sea sospechoso.
```

### Explicación de cada parte

| Sección | Propósito |
|---|---|
| Rol del analista | Establece el dominio de expertise para anclar el razonamiento del modelo |
| Tarea principal | Define el scope: Instagram DMs, phishing e ingeniería social |
| Instrucción de historial | Habilita el análisis contextual multi-turno |
| Estructura JSON exacta | Fuerza salida estructurada y parseable; evita texto libre |
| `No agregues texto fuera del JSON` | Previene que el modelo envuelva el JSON en explicaciones |
| IMPORTANTE — mensaje actual | Evita que el modelo "condene" mensajes normales por contexto previo |
| Criterios para HIGH | Reduce falsos positivos dando criterios explícitos de clasificación severa |

---

## 4. Estructura del user prompt

Archivo: `app/ai/groq_client.py`, función `analyze_conversation()`

```python
user_prompt = f"""Historial de la conversación:
{history_text}

Mensaje actual siendo analizado:
"{current_message}"

Resultados del análisis heurístico:
- URL score: {url_score:.2f}
- Text score: {text_score:.2f}
- Indicadores detectados:
{reasons_text}

Analizá si esta conversación representa un intento de phishing o ingeniería social."""
```

Donde `history_text` es generado por `_format_history()`:

```python
def _format_history(conversation_history: list[dict]) -> str:
    lines = []
    for msg in conversation_history[-10:]:
        sender = msg.get("sender_id_hash", "Usuario")
        text = msg.get("text", "")
        lines.append(f"Usuario {sender}: {text}")
    return "\n".join(lines)
```

El historial usa el `sender_id_hash` (primeros 12 hex del SHA256) en lugar del ID real — la anonimización se mantiene incluso dentro del prompt enviado a la IA externa.

---

## 5. Ejemplo real de input y output

### Input al modelo

**System prompt**: (el SYSTEM_PROMPT completo de arriba)

**User prompt**:
```
Historial de la conversación:
Usuario a3f1b2c4d5e6: Hola! vi tu perfil, sos muy linda
Usuario a3f1b2c4d5e6: te quiero mandar un regalo sorpresa
Usuario a3f1b2c4d5e6: necesito que verifiques tu cuenta primero

Mensaje actual siendo analizado:
"Entrá a este link para verificar: http://ig-verify-account.tk/login"

Resultados del análisis heurístico:
- URL score: 0.90
- Text score: 0.80
- Indicadores detectados:
- Blacklisted domain: ig-verify-account.tk
- Insecure HTTP: http://ig-verify-account.tk/login
- Suspicious keyword 'login' in URL
- support_impersonation
- credential_request
```

### Output del modelo

```json
{
  "risk_level": "HIGH",
  "confidence": 0.97,
  "explanation": "El mensaje contiene un link malicioso conocido que simula ser una verificación oficial de Instagram. Combinado con el historial de manipulación emocional, es un claro ataque de ingeniería social.",
  "recommendation": "No hagas clic en el link y bloqueá al remitente inmediatamente.",
  "patterns_detected": ["malicious_link", "credential_harvesting", "social_engineering", "fake_verification"]
}
```

---

## 6. Combinación del score heurístico con la confianza de la IA

El orquestador (`app/analysis/orchestrator.py`) combina ambas señales así:

```python
# Score final: se toma el máximo entre heurístico y confianza de Groq
final_score = max(heuristic_score, groq_confidence)

# Nivel de riesgo: se toma el más severo entre heurístico y Groq
_risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
if _risk_order[groq_risk] > _risk_order[risk_level]:
    risk_level = groq_risk
```

**Principio de diseño**: el sistema nunca baja el nivel de riesgo por la IA. Si el heurístico dice `HIGH` y Groq dice `MEDIUM`, el resultado final es `HIGH`. Esto minimiza falsos negativos a costa de posibles falsos positivos en casos edge.

---

## 7. Mecanismo de fallback si Groq no está disponible

La integración con Groq está envuelta en un bloque `try/except` en el orquestrador:

```python
try:
    history = await get_conversation_history(conversation_id, limit=10)
    groq_result = await groq_client.analyze_conversation(...)
    if groq_result:
        # aplica resultado de Groq
        ...
except Exception as exc:
    logger.warning("Groq integration skipped: %s", exc)
    # continúa con score heurístico sin IA
```

Dentro de `groq_client.py` hay dos niveles adicionales de fallback:

| Caso | Comportamiento |
|---|---|
| `GROQ_API_KEY` no configurada | Retorna `{}` inmediatamente sin llamar a la API |
| `json.JSONDecodeError` | Retorna `{"risk_level": "LOW", "confidence": 0.0}` |
| Cualquier otra excepción (timeout, red) | Retorna `{}` y el orquestrador continúa solo con heurística |

En todos los casos de fallo, el sistema **nunca se detiene**: opera con el score heurístico puro (`url_score × 0.6 + text_score × 0.4`).

---

## 8. Límites del plan gratuito de Groq

| Límite | Valor (plan gratuito) |
|---|---|
| Requests por minuto (RPM) | 30 RPM para `llama-3.3-70b-versatile` |
| Tokens por minuto (TPM) | 6,000 TPM |
| Tokens por día (TPD) | 1,000,000 TPD |
| Timeout configurado en el sistema | 10 segundos |

Con `max_tokens=512` y un user prompt de ~200 tokens, cada llamada consume aproximadamente **~700 tokens**. El plan gratuito permite aproximadamente **1,400 análisis por día** antes de alcanzar el límite diario de tokens.

> Si se supera el RPM (30 requests/minuto), Groq retorna HTTP 429. El sistema captura este error como `Exception` y activa el fallback heurístico automáticamente.
