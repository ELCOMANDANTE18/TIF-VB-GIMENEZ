# Plan de acción — Próxima sesión
**Generado:** 2026-06-14 (actualizado post-sesión)  
**Estado al cierre:** commit `3c9c548` — branch `main`

---

## SECCIÓN 1 — Estado al cierre de esta sesión

### Métricas actuales

```
Score global: 11/12 (92%)
Casos fallidos: TC08 (normal_after_phishing — el modelo IA prioriza la URL
                 de phishing en el historial sobre la retractación)

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
| `fd112c6` | feat(corpus/rag): fichas NIST/OWASP + retraction_cover + extra_context |
| `3c9c548` | docs(readme): actualizar metricas 11/12 (93.94% Macro F1) y corpus 16 fichas |

### Qué quedó funcionando y verificado

- **Tarea A completada** — 3 fichas NIST/OWASP agregadas al corpus ✓
  - `nist_otp_protection`: recuperada correctamente en TC07 ✓
  - `owasp_pretexting`: recuperada correctamente en TC09 ✓
  - `owasp_urgency_bypass`: recuperada correctamente en TC12 ✓
- **Tarea B completada (parcial)** — infraestructura lista, TC08 no se resuelve ✓
  - `extra_context` en `retrieve()` — retrocompatible (default `""`) ✓
  - Orchestrator y evaluador pasan `history[-1]` como contexto extra ✓
  - Ficha `retraction_cover` en corpus, se recupera en TC08 ✓
  - El modelo UM Cloud (95% confianza) igual clasifica HIGH por la URL del historial
- 16 fichas en el corpus (7 ataque + 2 MITRE + 2 Cialdini + 1 calibración + 4 nuevas) ✓
- Servidor arranca sin errores ✓
- 15 rutas registradas ✓
- Tokens de Instagram activos: `@fliagimenez2026` y `@gimenezbenja2` ✓
- Dashboard: 890 líneas en `router.py` — HTML en f-strings, funciona pero es deuda técnica

---

## SECCIÓN 2 — Tareas completadas en esta sesión

### ✅ Tarea A: Fichas NIST + OWASP (COMPLETADA)

3 fichas agregadas a `app/rag/corpus.py:296-411` (bloque `# ── MARCOS NORMATIVOS`):
- `nist_otp_protection` — NIST SP 800-63B (OTP protection)
- `owasp_pretexting` — OWASP Pretexting
- `owasp_urgency_bypass` — OWASP Artificial Time Pressure

**Verificación:** `evaluar_dataset.py` → 11/12 (92%), sin regresiones. Las fichas se recuperan correctamente en TC07, TC09 y TC12.

---

### ✅ Tarea B: Ficha de retractación (TC08) — COMPLETADA (con nota)

**Cambios aplicados a 4 archivos:**
- `app/rag/retriever.py:14` — nuevo parámetro `extra_context` (default `""`)
- `app/rag/retriever.py:29-31` — si hay `extra_context`, se agrega a `search_parts`
- `app/analysis/orchestrator.py:95` — pasa `history[-1]["texto"]` como `extra_context`
- `scripts/evaluar_dataset.py:120` — idem para la evaluación
- `app/rag/corpus.py:412-432` — ficha `retraction_cover`

**Resultado:** el RAG recupera correctamente `retraction_cover` en TC08, pero el modelo UM Cloud (95% confianza) clasifica HIGH porque ve la URL `portal-bradesco.digital` en el historial de la conversación. La infraestructura queda lista — el issue es del modelo, no del pipeline.

**Documentado como trabajo futuro** en `AUDITORIA_REPO.md` PARTE 9.4.

---

## SECCIÓN 3 — Tarea C (pendiente): Migración a Jinja2

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

## SECCIÓN 4 — Próxima sesión: Tarea C — Migración a Jinja2

### Fechas de referencia
- **Sesión de trabajo:** mañana (2026-06-15)
- **Demo:** viernes (4 días desde hoy)

### Única tarea pendiente

| Tarea | Riesgo | Tiempo estimado | Si sale mal |
|-------|--------|-----------------|-------------|
| **C: Migración Jinja2** | Alto | 4-6 horas | El dashboard puede quedar en blanco o con errores de template — requiere rollback completo del router.py y borrar templates/ |

### Nota sobre el estado actual

Las Tareas A y B están completadas. El sistema está listo para la demo con:
- **16 fichas** en el corpus RAG (NIST, OWASP, MITRE, Cialdini, calibración)
- **11/12 (92%)** — TC08 documentado como trabajo futuro
- **Dashboard funcional** con HTML en f-strings (deuda técnica, no bloqueante)

### Recomendación

```
Tarea C — Migración Jinja2 (4-6 horas)
  Solo si sobra tiempo después de la demo. NO hacer antes del viernes.
  Es mejora de calidad de código, no de funcionalidad.
  El sistema funciona perfectamente sin este cambio (tal como está ahora).
```

La migración está detallada paso a paso en la **Sección 3** de este documento (pasos 1-5, templates, checklist). Seguir ese orden.

---

*Documento actualizado 2026-06-14. Estado del sistema al cierre: commit `3c9c548`, 11/12 (92%), Macro F1 93.94%. Push enviado a `origin/main`.*
