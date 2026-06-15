# Mensajes de demo validados — Link Seguro

Fecha de validación: 2026-06-15  
Sistema: F1 93.94% (11/12) — estado confirmado antes de esta sesión  
Metodología: probados directamente contra `PhishingOrchestrator.analyze()` sin pasar por webhook ni Instagram

---

## Instrucciones de uso en la demo

**Desde qué cuenta mandar:** `hernestolopez2026` → `fliagimenez2026`  
**Orden:** LOW primero, MEDIUM segundo, HIGH tercero  
**Por qué ese orden:** permite mostrar en el dashboard la evolución del riesgo de la conversación de manera progresiva

**Qué esperar en el dashboard tras cada mensaje:**
- Ingresá a `/dashboard` con usuario `admin` / `admin123`
- Cada mensaje aparece en la conversación de hernestolopez2026 con su badge de riesgo
- En el panel de detalle se ve: score, categoría, técnica MITRE, explicación para el usuario
- En el mensaje HIGH: el sistema envía automáticamente una respuesta de alerta al remitente (si `ENABLE_AUTO_RESPONSE=True`)

---

## Mensaje 1 — LOW (conversación normal)

```
Hola! Vi tu perfil y me pareció buenísimo el contenido que subís. Seguí así!
```

**Resultado real del sistema:**

| Campo | Valor |
|---|---|
| `risk_level` | **LOW** |
| `score_final` | 0.147 |
| `score_texto` | 0.000 (ningún patrón activado) |
| `score_url` | 0.000 |
| `categoria` | none |
| `mitre` | none |
| `confianza_ia` | 0.98 |
| `lifecycle` | approach |
| `explicacion_usuario` | "El mensaje es un saludo cordial y un cumplido sin enlaces ni solicitudes de información sospechosa." |

**Qué activó:** nada. TextAnalyzer no encontró ningún patrón. La IA confirmó LOW con confianza 0.98.  
**Qué se ve en el dashboard:** badge gris LOW, sin alerta.

---

## Mensaje 2 — MEDIUM (impersonación de soporte, sin pedido directo)

```
Hola, somos el equipo de soporte oficial de Instagram. Detectamos actividad inusual en tu cuenta. Tu perfil podría quedar suspendido. Respondé a la brevedad para evitarlo.
```

**Resultado real del sistema:**

| Campo | Valor |
|---|---|
| `risk_level` | **MEDIUM** |
| `score_final` | 0.522 |
| `score_texto` | 1.000 |
| `score_url` | 0.000 |
| `categoria` | account_suspension_threat |
| `mitre` | T1566.003 |
| `confianza_ia` | 0.95 |
| `lifecycle` | approach |
| `explicacion_usuario` | "Cuidado: Este mensaje intenta hacerse pasar por el soporte de Instagram para asustarte con una suspensión. Instagram no contacta por DM para estos avisos. No respondas ni proporciones información." |

**Qué activó:**
- TextAnalyzer: `support_impersonation` (peso 0.6) + `urgency` (peso 0.5) → score_texto = 1.0
- RAG fichas: `owasp_pretexting`, `account_verification_scam`, `cialdini_authority`, `cialdini_urgency_scarcity`, `severity_calibration`
- La ficha `severity_calibration` le indicó a la IA que suplantación + urgencia **sin link ni código** → MEDIUM, no HIGH

**Qué se ve en el dashboard:** badge naranja MEDIUM, explicación visible para el operador.

---

## Mensaje 3 — HIGH (solicitud directa de OTP)

```
Hola, te mandé un código por error al tuyo. Me llegó un SMS con 6 números, ¿me lo podés reenviar? Es urgente, si no lo confirmo en las próximas horas pierdo acceso a mi cuenta.
```

**Resultado real del sistema:**

| Campo | Valor |
|---|---|
| `risk_level` | **HIGH** |
| `score_final` | 0.900 |
| `score_texto` | 0.500 (solo `urgency`) |
| `score_url` | 0.000 |
| `categoria` | otp_request |
| `mitre` | T1566.003 |
| `confianza_ia` | 1.00 |
| `lifecycle` | hook |
| `explicacion_usuario` | "¡Cuidado! Este mensaje es un intento de robo de cuenta. El atacante busca que le reenvíes un código de seguridad (OTP) para tomar control de tu perfil. Nunca compartas códigos de SMS con nadie." |

**Qué activó:**
- TextAnalyzer: solo `urgency` (el heurístico solo llega a 0.20 — no alcanza HIGH)
- RAG fichas: `otp_request` (keywords exactas: "SMS", "6 números", "reenviar"), `nist_otp_protection` ("te lo mandé por error", "6 números"), `mitre_T1566_003`
- La IA elevó de heurístico LOW/MEDIUM a HIGH con confianza 1.00 gracias al RAG
- Esto demuestra el valor del componente RAG: el heurístico solo no hubiera detectado este ataque

**Qué se ve en el dashboard:** badge rojo HIGH, respuesta automática enviada al remitente (si `ENABLE_AUTO_RESPONSE=True`).

---

## Por qué este set de mensajes es útil para la demo

- **Sin URLs:** ninguno contiene links, dominios ni acortadores → cero riesgo de que Meta marque las cuentas
- **Muestran los 3 niveles** de forma progresiva en una sola conversación
- **El caso HIGH** demuestra que el sistema detecta ataques sin URL — algo que los detectores basados solo en heurísticas de URL fallan
- **El caso MEDIUM** muestra la calibración fina: el sistema distingue "amenaza en construcción" de "ataque consumado"
- Los tres textos suenan naturales y creíbles para Instagram DM

---

## Estado del sistema al momento de la validación

```
Score final: 11/12 (92%)
F1 macro: 93.94%
Único fallo: TC08 (normal_after_phishing — esperado MEDIUM, obtenido HIGH)
```
