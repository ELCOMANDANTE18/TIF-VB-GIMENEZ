# Link Seguro — Demo para el tutor

Sistema de detección de phishing en DMs de Instagram con dashboard web
multi-usuario, autenticación con bcrypt + sesiones firmadas, y análisis
en vivo de mensajes que llegan por webhook desde Meta.

---

## 1. Pre-requisitos

- Python 3.12+ (el venv del repo está en `src/.venv`)
- SQLite 3 (viene con el sistema)
- ngrok 3 — **opcional**, solo si querés mostrar el webhook en vivo

Todas las dependencias Python ya están listadas en `src/requirements.txt`.
Si querés re-instalar en un venv limpio:

```bash
cd src
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## 2. Levantar el sistema (3 comandos)

```bash
# 1) Posicionarse en src/
cd src

# 2) Inicializar la base (idempotente: crea tablas si no existen)
.venv/bin/python database/init_db.py

# 3) Arrancar el servidor
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Listo. Abrir en navegador: **http://127.0.0.1:8000/login**

> Nota: la base ya viene con datos importados de Instagram para que
> el dashboard tenga conversaciones reales para mostrar. Si fuera la
> primera vez en una máquina limpia, además habría que correr:
> `.venv/bin/python scripts/setup_usuarios.py` para crear los usuarios.

---

## 3. Credenciales para probar las distintas vistas

| Usuario     | Password   | Rol   | Qué ve en el dashboard                         |
|-------------|------------|-------|------------------------------------------------|
| `admin`     | `admin123` | ADMIN | **Todo** — todas las conversaciones del sistema |
| `flia_test` | `link2024` | user  | 8 conversaciones (cuenta familiar histórica)   |
| `hernesto`  | `link2024` | user  | 0 conversaciones (cuenta sin DMs aún)          |
| `benja`     | `link2024` | user  | 9 conversaciones (mi cuenta personal real)     |

Para cambiar de usuario: botón **"Cerrar sesión"** arriba a la derecha
y volver a `/login`.

---

## 4. Recorrido sugerido para la demo

### Paso 1 — Mostrar el login
- Abrir `http://127.0.0.1:8000/login`
- Mostrar el formulario (estilo oscuro, mismo diseño que el dashboard)
- Intentar con una contraseña incorrecta → debe mostrar
  "Usuario o contraseña incorrectos"

### Paso 2 — Vista de administrador
- Loguearse como `admin` / `admin123`
- Mostrar el badge rojo **ADMIN** en el header
- Mostrar el dashboard con TODAS las conversaciones, ordenadas por riesgo
  (HIGH primero, luego MEDIUM, luego LOW)
- Click en una fila con riesgo HIGH para expandir el detalle:
  - Explicación para usuario final
  - Explicación técnica (analista)
  - Principios de Cialdini detectados (urgencia, autoridad, etc.)
  - URLs sospechosas con razón
  - Últimos 10 mensajes de la conversación
  - Categoría de ataque + técnica MITRE ATT&CK

### Paso 3 — Vista de usuario común (filtrado)
- Logout → loguearse como `benja` / `link2024`
- Mostrar que el badge ADMIN ya **no aparece** (es usuario común)
- Header dice "Bienvenido, @benja"
- Solo ve **sus 9 conversaciones**, no las de otros usuarios
- El conteo de tarjetas (Total / HIGH / MEDIUM / LOW) se recalcula
  para su cuenta solamente

### Paso 4 — Vista vacía (control)
- Logout → loguearse como `hernesto` / `link2024`
- Dashboard sin conversaciones, mensaje
  "No hay análisis registrados todavía"
- Demuestra que el filtro por `cuenta_monitoreada` funciona también
  cuando no hay datos

---

## 5. (Opcional) Webhook en vivo con ngrok

Solo si querés mostrar **un DM real entrando al sistema** durante la
demo. Requiere una terminal adicional y configuración previa en
Meta App Dashboard.

```bash
# Terminal 2 — túnel público
ngrok http 8000
# copiar la URL https://xxxxx.ngrok-free.dev

# Terminal 3 (opcional) — UI de ngrok para ver requests en vivo
xdg-open http://127.0.0.1:4040
```

En Meta App Dashboard (`developers.facebook.com/apps/<APP_ID>/webhooks/`):
- **Callback URL**: `https://xxxxx.ngrok-free.dev/webhook`
- **Verify Token**: `phishing_detector_2024`
- **Subscribed Fields**: `messages`

Cuando alguien le mande un DM a la cuenta suscripta, el sistema lo
recibe, lo guarda, lo analiza con el `PhishingOrchestrator` (URLs
sospechosas + patrones de texto + clasificación IA) y aparece en el
dashboard del usuario correspondiente en ~2 segundos.

---

## 6. Componentes técnicos destacables

- **FastAPI + SQLite** (sin ORM — SQL directo, decisión de simplicidad)
- **bcrypt** para hash de contraseñas (con fallback SHA256+salt si la
  librería no se puede importar)
- **itsdangerous** para firmar la cookie de sesión (HttpOnly, 8 h)
- **HTML inline en f-strings** (sin Jinja2 — todo en
  `app/dashboard/router.py`)
- **Multi-cuenta nativo**: el webhook es agnóstico, guarda cada DM con
  `cuenta_monitoreada = recipient_id` del payload, y el dashboard
  filtra `WHERE cuenta_monitoreada = usuario.ig_user_id` para no-admins.
  Cualquier usuario suscripto al sistema solo ve sus DMs.

---

## 7. Archivos clave para el tutor

| Archivo                          | Qué hay ahí                              |
|----------------------------------|------------------------------------------|
| `src/app/main.py`                | Entry point FastAPI                      |
| `src/app/dashboard/router.py`    | Login, logout, dashboard HTML            |
| `src/app/dashboard/auth.py`      | bcrypt + itsdangerous + sesiones         |
| `src/app/webhook/router.py`      | Recepción de webhooks de Meta            |
| `src/app/analysis/orchestrator.py` | Pipeline de análisis (URL + texto + IA) |
| `src/app/db/sqlite_client.py`    | Acceso a la BD (async, aiosqlite)        |
| `src/database/schema.sql`        | Esquema SQL completo                     |
| `src/scripts/setup_usuarios.py`  | Bootstrap de usuarios del dashboard      |
