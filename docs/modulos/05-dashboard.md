# Módulo: Dashboard

## Propósito

Interfaz web multiusuario para que los operadores revisen conversaciones clasificadas, vean el análisis completo de cada una (scores, MITRE, Cialdini, lifecycle, explicaciones) y descarguen reportes en PDF.

## Archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `app/dashboard/router.py` | Todas las rutas web: lista, detalle, login/logout, export PDF |
| `app/dashboard/auth.py` | Autenticación: hashing de contraseñas, cookies firmadas, sesiones |
| `app/dashboard/pdf_export.py` | Generación de PDFs de conversación con weasyprint |

## Funciones principales — auth.py

### `hash_password(password: str) → str`

Genera un hash bcrypt de la contraseña. Fallback a SHA-256 manual si `bcrypt` no está instalado.

### `verify_password(password: str, hashed: str) → bool`

Verifica una contraseña contra un hash bcrypt o SHA-256 (compatibilidad). Usa `bcrypt.checkpw()` si el hash no empieza con `sha256$`.

### `create_session_token(user_data: dict) → str`

Serializa `{id, username, ig_user_id, es_admin}` en un token firmado con `itsdangerous.URLSafeTimedSerializer`. El secreto viene de `settings.SESSION_SECRET`.

### `verify_session_token(token: str) → dict | None`

Deserializa y verifica la firma + expiración (8 horas). Devuelve `None` si la firma es inválida o el token expiró.

### `get_current_user(request: Request) → dict | None`

Lee la cookie `session` del request y la verifica. Es el guard de autenticación usado en todas las rutas del dashboard.

### `get_usuario_by_username(username: str) → dict | None`

Busca un usuario en `usuario_sistema` por `username` o `email`. Usado en el login.

## Funciones principales — router.py (rutas)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/login` | GET/POST | Formulario de login; POST verifica credenciales y setea cookie |
| `/logout` | GET | Elimina la cookie de sesión |
| `/dashboard` | GET | Lista de conversaciones ordenada por riesgo (HIGH primero) |
| `/conversacion/{id}` | GET | Detalle de conversación: timeline de mensajes + análisis completo |
| `/conversacion/{id}/pdf` | GET | Descarga PDF del análisis (requiere sesión) |
| `/health` | GET | Health check del sistema |

### Lógica de privacidad admin

```python
# Cuando es_admin=1, los mensajes se muestran con placeholder
if user.get("es_admin"):
    texto_visible = "[contenido protegido — solo visible para el operador]"
else:
    texto_visible = mensaje["texto"]
```

El admin ve el análisis técnico completo (scores, MITRE, Cialdini, lifecycle, URLs sospechosas) pero NO el texto real de los mensajes. El dueño de la cuenta (usuario regular) ve el texto completo. Ver `decisiones_tecnicas.md` #8.

## Funciones principales — pdf_export.py

### `render_pdf(id_conversacion: str) → bytes | None`

Genera un PDF completo de la conversación. Devuelve `None` si la conversación no existe.

**Contenido del PDF:**
- Badge de riesgo y fecha de exportación
- Score cards: URL / Texto / IA / Final
- Tabla de desglose con barras proporcionales
- Clasificación IA: categoría, MITRE, lifecycle, acción recomendada
- Principios de Cialdini detectados
- Explicación completa del analista
- URLs sospechosas
- Historial de mensajes (últimos 100, con truncación indicada)

**Tecnología:** `weasyprint 69.0` (HTML → PDF). El HTML usa CSS inline con Arial/sans-serif — sin fuentes externas para evitar llamadas de red durante la generación.

## Paleta visual y tecnología frontend

```
Background: #ECEAE3 (beige claro)
Cards:       #FFFFFF
Ink:         #1B1D1C
Sage:        #6E8F73 (acciones secundarias, LOW)
Danger:      #C2554B (HIGH risk)
Butter:      #B59628 (MEDIUM risk)
```

- **Tailwind CSS vía CDN** — utilidades de layout y espaciado
- **Fuentes**: Inter (texto) + JetBrains Mono (código, IDs técnicos)
- **Sin Jinja2** — todo el HTML generado inline en f-strings de Python. Ver `decisiones_tecnicas.md` #2.
- **Logo** servido desde `/static/logo.png` (montado en `main.py` como `StaticFiles`)

## Flujo de datos

```
Browser → GET /dashboard
    │
    ▼
get_current_user(request)    ← cookie "session" → verify_session_token()
    │ user dict
    ▼
SQLite: SELECT conversaciones ORDER BY risk_level_actual
    │
    ▼
HTML f-string con lista de conversaciones (badge de color por riesgo)

Browser → GET /conversacion/{id}
    │
    ▼
SQLite: conversacion + analisis_conversacion + mensajes (JOIN)
    │
    ▼
HTML f-string con timeline + panel de análisis
    │ [si es_admin=1] → texto de mensajes reemplazado por placeholder

Browser → GET /conversacion/{id}/pdf
    │
    ▼
pdf_export.render_pdf(id) → HTML → weasyprint → bytes
    │
    ▼
Response(content=pdf_bytes, media_type="application/pdf",
         headers={"Content-Disposition": 'attachment; filename="analisis_{id}.pdf"'})
```

## Decisiones de diseño

**Cookies firmadas sin JWT**: `itsdangerous` firma la cookie del lado del servidor con HMAC. No hay sesiones en DB — el token es stateless y expira a las 8 horas. Más simple que JWT para este caso de uso. Ver `src/docs/DECISIONES_ARQUITECTURA.md`.

**bcrypt con fallback SHA-256**: si `bcrypt` no está disponible en el entorno, el módulo usa SHA-256 con salt manual. Permite que el sistema arranque incluso sin la librería, aunque bcrypt es preferido para producción.

**HTML en f-strings**: deuda técnica aceptada por velocidad de desarrollo. El refactor a Jinja2 es mecánico y no afecta la lógica. Ver `decisiones_tecnicas.md` #2.

**weasyprint para PDF**: la alternativa (ReportLab, fpdf2) habría requerido reconstruir el layout desde cero. weasyprint convierte HTML → PDF manteniendo el CSS existente. La dependencia de librerías del sistema (`libpango`, `libcairo`) ya está instalada en el entorno.

## Estado actual

- [x] Login/logout con bcrypt + cookies firmadas (8h)
- [x] Lista de conversaciones con badges de color por riesgo
- [x] Panel de detalle con timeline y análisis completo
- [x] Privacidad admin (mensaje oculto para `es_admin=1`)
- [x] Exportación a PDF con `weasyprint` (últimos 100 mensajes)
- [x] Botón "Exportar PDF" en el dashboard
- [ ] Paginación en la lista de conversaciones (actualmente carga todo)
- [ ] Filtros por fecha o categoría de ataque
- [ ] Refactor a Jinja2 para separar lógica de presentación
