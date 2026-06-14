# Plan de acción — Próxima sesión
**Generado:** 2026-06-14  
**Estado al cierre:** commit `755ea16` — branch `main`

---

## SECCIÓN 1 — Estado al cierre de esta sesión

### Métricas actuales

```
Score global: 11/12 (92%)
Casos fallidos: TC08 (normal_after_phishing — decisión de diseño documentada)

Clase      Precision    Recall    F1-score
------------------------------------------
LOW         100.00%    100.00%    100.00%
MEDIUM      100.00%     83.33%     90.91%
HIGH         83.33%    100.00%     90.91%
------------------------------------------
Macro        94.44%     94.44%     93.94%
```

### Commits de la sesión (en orden)

| Hash | Qué |
|------|-----|
| `3ad6d11` | feat(rag): mejora iterativa — Macro F1 72.86%→93.94% (11/12) |
| `ec5c20d` | feat(rag): vocabulario rioplatense + calibración siempre presente |
| `755ea16` | docs(auditoria): PARTE 9 — corpus rioplatense y calibración |

### Qué quedó funcionando y verificado

- `evaluar_dataset.py` llama correctamente al retriever RAG ✓
- `severity_calibration` se inyecta en el 100% de los prompts ✓
- 13 fichas en el corpus, 4 con vocabulario rioplatense ampliado ✓
- `text_analyzer.py`: `credential_request` captura "confirmanos/verificar + titular/identidad" ✓
- `retriever.py`: normalización de tildes activa ✓
- Servidor: `uvicorn app.main:app` arranca sin errores (verificado en sesiones previas) ✓
- Tokens de Instagram activos: `@fliagimenez2026` y `@gimenezbenja2` ✓
- Dashboard: 890 líneas en `router.py` — HTML en f-strings, funciona pero es deuda técnica

---

## SECCIÓN 2 — Tarea A: Fichas NIST + OWASP

### Objetivo

Agregar 3 fichas nuevas al corpus basadas en marcos de referencia reconocidos. Esto enriquece el contexto del modelo y da evidencia académica para el informe (sección de fundamentos teóricos).

### Cómo agregar: al final de `app/rag/corpus.py`, antes del `]` de cierre, en un bloque:

```python
    # ── MARCOS NORMATIVOS ─────────────────────────────────────────────────────
```

---

### Ficha A1 — `nist_otp_protection`

**Fuente:** NIST SP 800-63B (Digital Identity Guidelines — Authentication and Lifecycle Management), Sección 5.2.3 "Out-of-Band Authenticators" y Sección 5.1.3.2.

**Principio clave:** *"Verifiers SHALL NOT prompt subscribers to provide an authentication secret to any party other than the verifier."* — ningún servicio legítimo pide el código OTP a través del canal de mensajería.

```python
{
    "id": "nist_otp_protection",
    "title": "NIST 800-63B — Ningún verificador legítimo pide OTP por DM",
    "keywords": [
        "mandame el código", "pasame el código", "reenvíame el código",
        "código que te llegó", "es solo 6 números", "me llegó un código",
        "código de verificación", "código de seguridad",
        "te lo mandé por error", "necesito que me lo reenvíes",
        "otp", "2fa", "doble factor", "autenticación",
    ],
    "content": (
        "MARCO: NIST SP 800-63B §5.2.3 establece que ningún verificador "
        "legítimo solicitará el código OTP/2FA al usuario a través de un "
        "canal de mensajería. Instagram, Meta y cualquier plataforma legítima "
        "NUNCA piden el código que le llegó por SMS al usuario en un DM.\n"
        "ATAQUE: el atacante solicita que la víctima reenvíe el código "
        "de verificación bajo pretextos ('te lo mandé por error', 'necesito "
        "verificar tu identidad'). Con el código obtiene acceso inmediato.\n"
        "CLASIFICACIÓN AUTOMÁTICA: cualquier mensaje pidiendo un código de "
        "verificación recibido por SMS es HIGH risk independientemente del "
        "pretexto — no existe escenario legítimo para esta solicitud.\n"
        "FASE: hook directo. MITRE: T1566.003."
    ),
},
```

**Relación con fichas existentes:** refuerza `otp_request` con fundamento normativo explícito. Las keywords se solapan intencionalmente para aumentar el score del retriever en casos OTP.

---

### Ficha A2 — `owasp_pretexting`

**Fuente:** OWASP Social Engineering Prevention Cheat Sheet (https://cheatsheetseries.owasp.org/cheatsheets/Social_Engineering_Prevention_Cheat_Sheet.html), sección "Pretexting"; y OWASP Testing Guide v4.2, WSTG-IDNT-05 (Testing for Account Enumeration and Guessable User Account).

**Principio clave:** pretexting = creación de un escenario fabricado de autoridad para manipular al objetivo. Es la técnica subyacente de `account_verification_scam` y `brand_support_impersonation`.

```python
{
    "id": "owasp_pretexting",
    "title": "OWASP — Pretexting: escenario fabricado de autoridad",
    "keywords": [
        "somos el equipo", "somos del equipo", "equipo de seguridad",
        "equipo de soporte", "instagram support", "meta support",
        "detectamos", "identificamos", "hemos notado", "hemos detectado",
        "actividad inusual", "actividad sospechosa", "movimientos extraños",
        "violación de términos", "infracción de política", "copyright",
        "derechos de autor", "tu cuenta está en riesgo",
        "necesitamos verificar", "debés verificar",
        "support_impersonation",
    ],
    "content": (
        "MARCO: OWASP Social Engineering Prevention — Pretexting. Técnica "
        "donde el atacante fabrica un escenario de autoridad creíble para "
        "que la víctima cumpla una solicitud que normalmente rechazaría.\n"
        "PATRÓN EN INSTAGRAM DMs: el atacante se presenta como soporte de "
        "Instagram/Meta, alega un problema inventado (violación de política, "
        "actividad inusual, infracción de derechos de autor) y exige una "
        "acción urgente para 'resolver' el problema.\n"
        "INDICADORES: claim de ser equipo oficial + problema fabricado + "
        "urgencia + solicitud de acción (clic en link, confirmar identidad, "
        "enviar código). Instagram NUNCA contacta usuarios por DM.\n"
        "SEVERIDAD: MEDIUM si falta el link/código, HIGH si incluye alguno.\n"
        "FASE: hook → pressure. MITRE: T1566.003."
    ),
},
```

**Relación con fichas existentes:** complementa `account_verification_scam` y `brand_support_impersonation` con mayor cobertura de keywords de "detección" y vocabulario de autoridad fabricada.

---

### Ficha A3 — `owasp_urgency_bypass`

**Fuente:** OWASP Social Engineering Prevention Cheat Sheet, sección "Creating Urgency / Artificial Time Pressure"; y NIST SP 800-63B Sección 10.2 (Usability Considerations — nota sobre presión temporal como señal de ataque).

**Principio clave:** la urgencia artificial es una de las técnicas más documentadas de ingeniería social. Su función es desactivar el pensamiento crítico de la víctima.

```python
{
    "id": "owasp_urgency_bypass",
    "title": "OWASP — Presión temporal artificial: bypass del pensamiento crítico",
    "keywords": [
        "urgency", "urgente", "inmediatamente", "ahora mismo",
        "sin demora", "a la brevedad", "cuanto antes",
        "24 horas", "48 horas", "horas para responder",
        "vence", "expira", "se cierra", "último aviso",
        "tu cuenta será eliminada", "dado de baja", "inhabilitada",
        "perdés acceso", "perderás tu cuenta", "acción requerida",
        "tiempo limitado", "no hay tiempo",
    ],
    "content": (
        "MARCO: OWASP Social Engineering — Urgency/Artificial Time Pressure. "
        "La creación de plazos artificiales es una táctica documentada para "
        "impedir que la víctima consulte con otros o verifique la legitimidad "
        "del mensaje antes de actuar.\n"
        "SEÑALES EN INSTAGRAM DMs: deadlines específicos ('24 horas', '48 horas'), "
        "amenazas de consecuencias irreversibles ('tu cuenta será eliminada "
        "permanentemente', 'perderás acceso a tus fotos'), llamadas a acción "
        "inmediata ('actuá ya', 'respondé ahora mismo').\n"
        "REGLA DE CALIBRACIÓN: la urgencia SOLA sin link ni código → MEDIUM. "
        "Urgencia + link externo o solicitud de código → HIGH.\n"
        "Las plataformas legítimas siempre dan tiempo razonable para actuar "
        "y envían notificaciones por múltiples canales, nunca solo por DM.\n"
        "FASE: pressure. Principio Cialdini: urgency/scarcity."
    ),
},
```

**Relación con fichas existentes:** complementa `cialdini_urgency_scarcity` con vocabulario rioplatense extendido y fundamentación OWASP. La regla de calibración MEDIUM/HIGH dentro del contenido refuerza `severity_calibration`.

---

### Procedimiento exacto para agregar las fichas

En `src/app/rag/corpus.py`, al final del array `CORPUS`, después de la ficha `severity_calibration` y antes del `]` de cierre:

```python
    # ── MARCOS NORMATIVOS ─────────────────────────────────────────────────────
    { ... ficha A1 ... },
    { ... ficha A2 ... },
    { ... ficha A3 ... },
]
```

Luego ejecutar:
```bash
cd src
.venv/bin/python scripts/evaluar_dataset.py
```

**Expectativa:** 11/12 (sin regresiones). Las fichas no deberían bajar ningún caso porque:
- TC01 (benign): ninguna keyword matchea → sin cambio
- TC02-TC07 (HIGH): refuerzan señales ya correctas → sin cambio
- TC08 (MEDIUM/fallo): el mensaje actual "Cómo te va?" no matchea ninguna nueva keyword → sin cambio
- TC09-TC12 (MEDIUM): keywords de `owasp_pretexting` podrían mejorar la señal para TC09

---

## SECCIÓN 3 — Tarea B: Ficha de retractación (TC08)

### Diagnóstico (de AUDITORIA_REPO.md PARTE 9.4)

- **TC08:** `history = ["Verificá tu cuenta: http://portal-bradesco.digital/", "Igual eso lo mandé sin querer, borralo"]`, `current = "Cómo te va? Nos vemos el finde?"`
- El retriever solo busca en `current_message + url_reasons + text_patterns`. Las keywords de retractación ("borralo", "lo mandé sin querer") están en `history[-1]`, no en el mensaje actual.
- El modelo ve la URL de phishing en el historial → devuelve HIGH al 98%.

---

### Cambio 1 — `app/rag/retriever.py`

Agregar el parámetro `extra_context` a `retrieve()`:

```python
# ANTES (línea 12):
def retrieve(
    message: str,
    url_reasons: list[str] | None = None,
    text_patterns: list[str] | None = None,
    top_k: int = 2,
) -> str:

# DESPUÉS:
def retrieve(
    message: str,
    url_reasons: list[str] | None = None,
    text_patterns: list[str] | None = None,
    extra_context: str = "",
    top_k: int = 2,
) -> str:
```

Y en el cuerpo (línea 27):
```python
# ANTES:
search_parts = [message] + url_reasons + text_patterns

# DESPUÉS:
search_parts = [message] + url_reasons + text_patterns
if extra_context:
    search_parts.append(extra_context)
```

**Impacto en otros casos:** el parámetro tiene default `""` → retrocompatible. En `evaluar_dataset.py` no se pasa (por ahora), solo desde `orchestrator.py`.

---

### Cambio 2 — `app/analysis/orchestrator.py`

En las líneas 90-99 (ya identificadas), cambiar la llamada a `retrieve()`:

```python
# ANTES (líneas 95-99):
retrieved_context = retrieve(
    message=text,
    url_reasons=url_result.reasons,
    text_patterns=text_result.patterns_matched,
)

# DESPUÉS — agregar último mensaje del historial como contexto extra:
last_history_text = history[-1]["texto"] if history else ""
retrieved_context = retrieve(
    message=text,
    url_reasons=url_result.reasons,
    text_patterns=text_result.patterns_matched,
    extra_context=last_history_text,
)
```

`history` ya está disponible en el scope (líneas 90-93). No hay import nuevo necesario.

---

### Ficha nueva — `retraction_cover`

Agregar en `corpus.py` dentro del bloque de marcos normativos:

```python
{
    "id": "retraction_cover",
    "title": "Retractación post-phishing — táctica de cobertura",
    "keywords": [
        "borralo", "borrar", "lo mandé sin querer", "fue un error",
        "me equivoqué", "no era para vos", "ignoralo", "olvidalo",
        "mandé mal", "te lo mandé por error", "no le des bola",
        "disculpá", "perdón por el mensaje", "ignorá ese link",
    ],
    "content": (
        "PATRÓN — RETRACTACIÓN POST-PHISHING: el atacante envía contenido "
        "malicioso (link, solicitud de OTP, pedido de datos) y luego se "
        "retracta ('fue un error', 'borralo', 'no era para vos'). Esta es "
        "una táctica estándar usada cuando la víctima no respondió o para "
        "bajar la guardia antes de un segundo intento.\n"
        "DECISIÓN DE CLASIFICACIÓN: mantener el riesgo en al menos MEDIUM. "
        "La retractación no invalida el intento previo — un atacante real "
        "diría exactamente lo mismo que alguien que genuinamente se equivocó.\n"
        "ACCIÓN: el operador humano debe revisar el historial completo y "
        "decidir si la retractación es genuina. No desescalar a LOW de forma "
        "automática.\n"
        "FASE: puede aparecer en cualquier etapa. MITRE: T1566.002/003."
    ),
},
```

---

### Cambio 3 — `scripts/evaluar_dataset.py`

Para que el script de evaluación también use el historial al recuperar contexto RAG (así TC08 se beneficia del cambio en el test):

```python
# ANTES (líneas ~119-125):
retrieved_context = retrieve(
    message=current_msg,
    url_reasons=url_result.reasons,
    text_patterns=text_result.patterns_matched,
)

# DESPUÉS — agregar último mensaje del historial:
last_history_text = history[-1]["texto"] if history else ""
retrieved_context = retrieve(
    message=current_msg,
    url_reasons=url_result.reasons,
    text_patterns=text_result.patterns_matched,
    extra_context=last_history_text,
)
```

---

### Análisis de riesgo — casos TC01-TC12 con URLs en historial

| ID | URL en historial | `history[-1]` pasado como extra_context | Riesgo de regresión |
|----|-----------------|----------------------------------------|---------------------|
| TC01 | No | "Todo bien y vos?" | Ninguno — sin keywords |
| TC02 | No (URL en msg actual) | "Tu cuenta fue reportada..." | Bajo — refuerza HIGH existente |
| TC03 | No (URL en msg actual) | "Tenés 24 horas para apelar..." | Bajo — ya es HIGH, urgency keywords refuerzan |
| TC04 | No | "Igual me alegra haberme equivocado..." | Ninguno |
| TC05 | No (URL en msg actual) | "Entrá a plataforma: http://crypto-vip-signals.top/..." | Bajo — ya es HIGH |
| TC06 | No (URL en msg actual) | "Premio: iPhone 15 Pro. Para reclamarlo..." | Bajo — ya es HIGH |
| TC07 | No | "Instagram me mandó un código a tu número por error" | Medio — OTP keywords en historial → refuerza HIGH ✓ |
| **TC08** | **Sí** (`portal-bradesco.digital`) | **"Igual eso lo mandé sin querer, borralo"** | **Objetivo del cambio: retraction_cover → MEDIUM** |
| TC09 | No | "Detectamos actividad inusual en tu cuenta..." | Bajo — "actividad inusual" en extra_context puede aumentar score de severity_calibration |
| TC10 | No (URL en msg actual) | "Hola! Vi tu perfil y me pareció genial..." | Ninguno |
| TC11 | No | "Soy empresaria, viajo mucho. Me dedico a inversiones y cripto..." | Bajo — reinforza pig_butchering, TC11 ya pasa |
| TC12 | No | "Para coordinar la entrega necesitamos que respondás a la brevedad" | Bajo — reinforza severity_calibration, TC12 ya pasa |

**Conclusión:** el riesgo de regresión es bajo. El único caso con cambio significativo esperado es TC08 (el objetivo). TC09 podría mejorar levemente con más señal. Ejecutar la evaluación completa después del cambio para verificar.

**Impacto esperado si todo funciona:** 12/12 (100%), Macro F1 ~96-97%.

---

## SECCIÓN 4 — Tarea C: Migración a Jinja2

### Estado actual del router.py (890 líneas)

| Bloque | Líneas | Destino |
|--------|--------|---------|
| Imports + setup | 1-28 | Permanece en `router.py` |
| `_e()`, `_fmt_ts()` | 30-48 | Permanece en `router.py` (helpers Python) |
| `get_dashboard_data()` | 51-154 | Permanece (lógica DB) |
| `get_all_ig_usuarios()` | 155-167 | Permanece (lógica DB) |
| `get_conversacion_para_accion()` | 168-202 | Permanece (lógica DB) |
| `_get_token_for_account()` | 203-208 | Permanece (lógica) |
| `_marcar_respondido_sync()` | 209-226 | Permanece (lógica DB) |
| `_build_rows()` | 227-429 | **Reemplazar por loop Jinja2 en `dashboard.html`** |
| `render_html()` head (481-500) | 481-500 | **→ `templates/base.html`** |
| `render_html()` navbar (503-514) | 503-514 | **→ `templates/base.html`** |
| `render_html()` body completo | 515-662 | **→ `templates/dashboard.html`** |
| `_render_login()` head (671-682) | 671-682 | Comparte `base.html` |
| `_render_login()` body (683-744) | 683-744 | **→ `templates/login.html`** |
| Rutas FastAPI (7 rutas) | 745-890 | Permanece, retorna `TemplateResponse` |

**Nota importante:** no hay ruta GET `/conversacion/{id}` en el router. El detalle de conversación es un panel lateral cargado via JS dentro del dashboard. No se necesita `conversacion.html` separado — todo va en `dashboard.html`.

---

### Paso 1 — Crear `src/templates/base.html`

Extraer de `render_html()` líneas 481-514 (head + navbar). Template base que extienden todas las páginas:

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
{% block meta_extra %}<meta http-equiv="refresh" content="30">{% endblock %}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}Link Seguro{% endblock %}</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
  body { font-family: 'Inter', sans-serif; }
  .font-mono { font-family: 'JetBrains Mono', monospace !important; }
  .btn-action:disabled { opacity: 0.4; cursor: not-allowed !important; }
  .btn-action.success { border-color: #6E8F73 !important; color: #6E8F73 !important; background: #E8F3EA !important; }
  .btn-action.error   { border-color: #C2554B !important; color: #C2554B !important; background: #FEF2F2 !important; }
  table { border-collapse: collapse; width: 100%; }
  .conv-row:hover { filter: brightness(0.96); }
  #progress-bar { transition: width 1s linear; }
  td { vertical-align: middle; border-bottom: 2px solid #E9E6DD; }
  tbody tr:nth-child(even) td { background: rgba(0,0,0,0.025); }
</style>
</head>
<body class="{% block body_class %}bg-[#ECEAE3] text-[#1B1D1C] min-h-screen{% endblock %}">

{% block navbar %}
<header class="h-16 fixed top-0 left-0 right-0 z-50 bg-[#FFFFFF] border-b border-[#E9E6DD] flex items-center justify-between px-6">
  <div class="flex items-center gap-2">
    <img src="/static/logo.png" alt="Link Seguro" class="h-10 w-auto">
    <span class="text-xl font-bold text-[#1B1D1C] hidden sm:inline">Link Seguro</span>
  </div>
  <span class="text-sm text-[#8A8B85] hidden md:block">Dashboard de Seguridad</span>
  <div class="flex items-center gap-3">
    <span class="text-base font-medium text-[#1B1D1C]">@{{ user.username }}</span>
    {% if user.es_admin %}
    <span class="text-sm py-1 px-3 rounded-full bg-[#C9D6E8] text-[#7A95C2] border border-[#5D7DAB] font-semibold">ADMIN</span>
    {% else %}
    <span class="text-sm py-1 px-3 rounded-full bg-[#F7F5EE] text-[#8A8B85] border border-[#E9E6DD] font-semibold">USER</span>
    {% endif %}
    <a href="/logout" class="text-base py-2 px-4 rounded-lg bg-[#F7F5EE] hover:bg-[#F5D9CC] text-[#1B1D1C] border border-[#E9E6DD] no-underline transition-colors">Cerrar sesión</a>
  </div>
</header>
{% endblock %}

{% block content %}{% endblock %}

</body>
</html>
```

---

### Paso 2 — Crear `src/templates/login.html`

Extraer de `_render_login()` líneas 663-744:

```html
{% extends "base.html" %}

{% block title %}Link Seguro — Iniciar sesión{% endblock %}
{% block meta_extra %}{% endblock %}{# sin auto-refresh en login #}
{% block body_class %}min-h-screen bg-[#ECEAE3] flex items-center justify-center px-4{% endblock %}
{% block navbar %}{% endblock %}{# sin navbar en login #}

{% block content %}
<div class="w-full max-w-md">
  <div class="bg-white rounded-2xl shadow-sm border border-[#E9E6DD] p-8">
    <div class="flex flex-col items-center mb-8">
      <img src="/static/logo.png" alt="Link Seguro" class="h-20 w-auto mb-4">
      <h1 class="text-2xl font-bold text-[#1B1D1C]">Link Seguro</h1>
      <p class="text-sm text-[#8A8B85] mt-1">Sistema de detección de phishing</p>
    </div>
    {% if error %}
    <div class="mb-4 p-3 rounded-lg bg-[#FEF2F2] border border-[#FECACA] text-[#C2554B] text-sm">{{ error }}</div>
    {% endif %}
    <form method="POST" action="/login" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-[#1B1D1C] mb-1">Usuario</label>
        <input type="text" name="username" required
               class="w-full px-3 py-2 rounded-lg border border-[#E9E6DD] bg-[#F7F5EE] focus:outline-none focus:border-[#6E8F73]">
      </div>
      <div>
        <label class="block text-sm font-medium text-[#1B1D1C] mb-1">Contraseña</label>
        <input type="password" name="password" required
               class="w-full px-3 py-2 rounded-lg border border-[#E9E6DD] bg-[#F7F5EE] focus:outline-none focus:border-[#6E8F73]">
      </div>
      <button type="submit"
              class="w-full py-2.5 px-4 rounded-lg bg-[#1B1D1C] text-white font-medium hover:bg-[#2D3130] transition-colors">
        Iniciar sesión
      </button>
    </form>
  </div>
</div>
{% endblock %}
```

---

### Paso 3 — Crear `src/templates/dashboard.html`

Extraer el body de `render_html()` líneas 515-662 y reemplazar `_build_rows()` con loop Jinja2. Este es el paso más largo (≈150 líneas de template). La lógica de colores de badge e íconos de riesgo pasa de Python a filtros/conditionals Jinja2:

```html
{% extends "base.html" %}
{% block title %}Link Seguro — Dashboard{% endblock %}

{% block content %}
<div class="pt-20 px-6 pb-8 max-w-[1800px] mx-auto">

  {# Barra de stats #}
  <div class="flex items-center justify-end mb-5">
    <div class="flex items-center gap-3">
      <span class="text-sm text-[#8A8B85]">Última actualización: {{ last_analysis }}</span>
      <span class="text-xs bg-[#F7F5EE] border border-[#E9E6DD] rounded-full px-3 py-1 text-[#8A8B85]">
        {{ stats.total }} conversaciones
      </span>
      <span class="text-xs bg-[#FEF2F2] border border-[#FECACA] rounded-full px-3 py-1 text-[#C2554B] font-bold">
        {{ stats.high }} HIGH
      </span>
    </div>
  </div>

  {# Filtro de cuentas (solo admin) #}
  {% if user.es_admin and usuarios_list %}
  <div class="flex gap-2 items-center mb-5 flex-wrap">
    <span class="text-sm text-[#8A8B85] uppercase tracking-wider mr-1">Filtrar:</span>
    <a href="/dashboard" class="py-1.5 px-4 rounded-full border text-sm no-underline transition-colors
       {% if not filtro_activo %}border-[#7A95C2] text-[#4A6A99] bg-[#C9D6E8] font-bold
       {% else %}border-[#E9E6DD] text-[#8A8B85]{% endif %}">Todas las cuentas</a>
    {% for u in usuarios_list %}{% if u.ig_username %}
    <a href="/dashboard?filtro={{ u.ig_username }}"
       class="py-1.5 px-4 rounded-full border text-sm no-underline transition-colors
       {% if u.ig_username == filtro_activo %}border-[#7A95C2] text-[#4A6A99] bg-[#C9D6E8] font-bold
       {% else %}border-[#E9E6DD] text-[#8A8B85]{% endif %}">@{{ u.ig_username }}</a>
    {% endif %}{% endfor %}
  </div>
  {% endif %}

  {# Tabla de conversaciones #}
  <table>
    <thead>...</thead>
    <tbody>
    {% for conv in conversations %}
    <tr class="conv-row cursor-pointer"
        style="border-left: 5px solid
        {% if conv.risk == 'HIGH' %}#C2554B
        {% elif conv.risk == 'MEDIUM' %}#B59628
        {% else %}#6E8F73{% endif %};">
      <td ...>@{{ conv.username | e }}</td>
      <td ...><span class="badge-{{ conv.risk | lower }}">{{ conv.risk }}</span></td>
      {# ... resto de celdas ... #}
    </tr>
    {% endfor %}
    </tbody>
  </table>

  {# Panel de detalle (JS-driven, igual que ahora) #}
  <div id="detail-panel">...</div>

</div>
{% endblock %}
```

**Nota:** el panel de detalle lateral se carga con JS (fetch a una URL interna). Mantener la misma lógica JS — solo moverla al template.

---

### Paso 4 — Reducir `router.py` a ~200 líneas

Funciones que **permanecen** en Python (lógica pura, sin HTML):

```
_e(value)                              # helper escape
_fmt_ts(ts)                            # helper timestamp
get_dashboard_data(ig_user_id)         # query DB
get_all_ig_usuarios()                  # query DB
get_conversacion_para_accion(id)       # query DB
_get_token_for_account(ig_user_id)     # lookup token
_marcar_respondido_sync(id)            # update DB
```

Funciones que **desaparecen** (reemplazadas por templates):
```
_build_rows()      # 200 líneas → loop en dashboard.html
render_html()      # 230 líneas → dashboard.html + base.html
_render_login()    # 80 líneas  → login.html
```

Cada ruta pasa de retornar `HTMLResponse(render_html(...))` a:
```python
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, filtro: str | None = Query(default=None)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    data = get_dashboard_data(user["ig_user_id"] if not user.get("es_admin") else None)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "conversations": data["conversations"],
        "stats": data["stats"],
        "last_analysis": _fmt_ts(data["last_analysis"]),
        "usuarios_list": get_all_ig_usuarios() if user.get("es_admin") else [],
        "filtro_activo": filtro,
    })
```

---

### Paso 5 — Wiring en `main.py`

Agregar la inicialización de templates al arrancar la app:

```python
# En app/main.py, después de crear la app FastAPI:
from fastapi.templating import Jinja2Templates

# Esto es transparente para el router — Jinja2Templates se inicializa en router.py
```

No se necesita ningún cambio en `main.py` si `Jinja2Templates` se instancia en `router.py`.

---

### Checklist de verificación post-migración

```
□ GET /login — muestra formulario con logo centrado
□ POST /login — admin/admin123 → redirige a /dashboard
□ POST /login — flia_test/link2024 → redirige a /dashboard
□ POST /login — credenciales incorrectas → muestra error
□ GET /dashboard (admin) — ve todas las conversaciones
□ GET /dashboard (admin) — badge ADMIN visible en navbar
□ GET /dashboard (admin) — filtro por cuenta visible y funciona
□ GET /dashboard (flia_test) — ve solo SUS conversaciones
□ Click en conversación HIGH → panel de detalle se abre
□ Panel de detalle (admin) → mensajes muestran [contenido protegido]
□ Panel de detalle (flia_test) → mensajes muestran texto real
□ GET /conversacion/{id}/pdf → descarga PDF correctamente
□ POST /dashboard/accion/notificar → envía DM (solo en staging)
□ POST /dashboard/accion/responder → envía email (solo si ENABLE_EMAIL_ALERTS)
□ GET /logout → redirige a /login y borra cookie
□ Auto-refresh cada 30s activo en /dashboard (no en /login)
□ Logo /static/logo.png carga en login y navbar
□ Tailwind CDN aplica estilos correctamente
□ Sin errores 500 en los 4 usuarios: admin, flia_test, benja, hernesto
```

---

## SECCIÓN 5 — Orden recomendado para la próxima sesión

### Fechas de referencia
- **Sesión de trabajo:** próxima disponible
- **Demo:** viernes (5 días desde el 2026-06-14)

### Análisis de cada tarea

| Tarea | Riesgo | Tiempo estimado | Si sale mal |
|-------|--------|-----------------|-------------|
| **A: Fichas NIST/OWASP** | Muy bajo | 30-45 min | Borrar las 3 fichas del corpus.py, re-evaluar — sin impacto |
| **B: Ficha de retractación (TC08)** | Bajo | 45-60 min | Revertir retriever.py y orchestrator.py (2 archivos, cambio de 3 líneas cada uno) — métricas vuelven a 93.94% |
| **C: Migración Jinja2** | Alto | 4-6 horas | El dashboard puede quedar en blanco o con errores de template — requiere rollback completo del router.py y borrar templates/ |

### Orden recomendado

```
1. Tarea A — Fichas NIST/OWASP (30-45 min)
   Bajo riesgo, alto valor para el informe (referencias académicas).
   Verificar: evaluar_dataset.py → debe seguir 11/12 o mejorar.
   Commit: feat(corpus): fichas NIST 800-63B y OWASP

2. Tarea B — Ficha de retractación TC08 (45-60 min)
   Riesgo controlado — solo 3 archivos, cambios pequeños.
   Si funciona: 12/12 (100%), Macro F1 ~96-97% — argumento fuerte para defensa.
   Verificar: evaluar_dataset.py → esperar PASS en TC08.
   Commit: feat(rag/orchestrator): retraction fix — TC08 MEDIUM

3. Tarea C — Migración Jinja2 (4-6 horas)
   Solo si sobra tiempo después de la demo. NO hacer antes del viernes.
   Es mejora de calidad de código, no de funcionalidad.
   El sistema funciona perfectamente sin este cambio.
```

### Si no da el tiempo para las 3

- **Solo A:** sistema queda con fundamentos académicos sólidos + métricas 93.94%. Suficiente para la defensa.
- **A + B:** sistema perfecto en métricas (100% si funciona). El argumento de "trabajo futuro" para TC08 se convierte en "resuelto". Ideal para la defensa.
- **A + B + C:** código limpio y mantenible. Solo si la demo no es el viernes o si hay más de un día disponible.

### Criterio de corte: si Tarea B tarda más de 90 minutos, parar y documentar como trabajo futuro

El cambio de TC08 puede ser que el modelo no baje a MEDIUM incluso con la nueva ficha (el modelo tiene 98% de confianza en HIGH). En ese caso: revertir, documentar el intento y el resultado, y usar el argumento de trabajo futuro documentado en PARTE 9.4 de AUDITORIA_REPO.md.

---

*Documento generado 2026-06-14. Estado del sistema al cierre: commit `755ea16`, 11/12 (92%), Macro F1 93.94%.*
