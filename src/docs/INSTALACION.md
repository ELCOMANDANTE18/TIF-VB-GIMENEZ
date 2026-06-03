# Link Seguro — Guía de Instalación y Puesta en Marcha

## 1. Requisitos previos

### Software

| Requisito | Versión mínima | Verificar con |
|---|---|---|
| Python | 3.10+ | `python --version` |
| git | cualquier | `git --version` |
| ngrok | 3.x | `ngrok --version` |
| sqlite3 | 3.x (incluido en Python) | `sqlite3 --version` |

### Cuentas necesarias

- **Meta for Developers**: cuenta en `developers.facebook.com` con acceso a crear apps tipo Negocios.
- **UM Cloud**: cuenta `@um.edu.ar` con acceso a `ai.cloud.um.edu.ar` y una API key generada en el portal institucional.
- **ngrok**: cuenta gratuita en `ngrok.com` para obtener un dominio estático (o usar el dominio efímero).

---

## 2. Instalación paso a paso

### 2.1 Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd TIF-VB-GIMENEZ/src
```

### 2.2 Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2.3 Crear el archivo de configuración

```bash
cp .env.example .env
# Editar .env con los valores reales (ver sección 3)
```

### 2.4 Inicializar la base de datos

```bash
python database/init_db.py
```

Salida esperada:
```
Base de datos lista en /ruta/absoluta/src/data/phishing_detector.db
```

### 2.5 (Opcional) Importar blacklist de PhishTank

```bash
# Descargar phishtank.csv desde phishtank.org
# y colocarlo en data/blacklist/phishtank.csv
python scripts/update_blacklist.py
```

---

## 3. Configuración del .env

```env
# ── Meta / Instagram ──────────────────────────────────────────
# ID numérico de la página de Facebook vinculada a la cuenta IG
FACEBOOK_PAGE_ID=123456789012345

# ID de la app creada en developers.facebook.com
META_APP_ID=987654321098765

# App Secret de la app de Meta (Configuración > Básica)
META_APP_SECRET=abc123def456...

# Token arbitrario que se configura también en Meta Webhook
META_VERIFY_TOKEN=mi_token_secreto_para_verificacion

# Page Access Token con permisos instagram_manage_messages
PAGE_ACCESS_TOKEN=EAAxxxxxxxxxxxxx...

# ── Cuenta monitoreada ────────────────────────────────────────
# Instagram User ID de la cuenta que se monitorea
FLIA_TEST_IG_USER_ID=123456789

# Token de acceso de esa cuenta específica (si difiere del PAGE_ACCESS_TOKEN)
FLIA_TEST_TOKEN=EAAxxxxxxxxxxxxx...

# ── UM Cloud IA ───────────────────────────────────────────────
# API key generada en ai.cloud.um.edu.ar
UM_API_KEY=um-xxxxxxxxxxxxxxxxxxxx

# URL base del endpoint UM Cloud (no modificar salvo cambio institucional)
UM_BASE_URL=https://ai.cloud.um.edu.ar/api/v1

# Modelo a usar
UM_MODEL=gemma4-26b

# ── Umbrales de clasificación (opcionales, defaults incluidos) ─
# Score >= 0.7 → HIGH
RISK_THRESHOLD_HIGH=0.7
# Score >= 0.4 → MEDIUM
RISK_THRESHOLD_MEDIUM=0.4
# Peso del score de URLs en el heurístico
URL_WEIGHT=0.6
# Peso del score de texto en el heurístico
TEXT_WEIGHT=0.4
```

**Importante**: nunca commitear el `.env` real. El `.gitignore` ya excluye `*.env` y `.env`.

---

## 4. Configuración de Meta for Developers

### 4.1 Crear la app

1. Ir a `developers.facebook.com` → "Mis apps" → "Crear app"
2. Tipo de app: **Negocios**
3. Nombre: `LinkSeguro` (o el nombre de tu elección)
4. Email de contacto: tu email universitario
5. Guardar y continuar

### 4.2 Agregar el producto Instagram

1. En el dashboard de la app → "Agregar productos"
2. Seleccionar **Instagram** → "Configurar"
3. En "Configuración" de Instagram → agregar la cuenta de Instagram a monitorear como cuenta de prueba

### 4.3 Generar el Page Access Token

1. Herramientas → Explorador de la API de Graph
2. Seleccionar la app y la página vinculada
3. Agregar permisos: `instagram_manage_messages`, `pages_messaging`
4. Generar token → copiar a `PAGE_ACCESS_TOKEN` en `.env`

### 4.4 Configurar el webhook

1. En la app de Meta → Webhooks → Agregar webhook
2. **URL de callback**: `https://TU-DOMINIO-NGROK.ngrok-free.app/webhook`
3. **Token de verificación**: el mismo valor que `META_VERIFY_TOKEN` en `.env`
4. Suscribirse al campo: `messages`
5. Verificar y guardar (ngrok debe estar corriendo antes de este paso)

### 4.5 Agregar evaluadores/testers

Para poder recibir mensajes en modo de desarrollo (sin publicar la app):
1. Configuración de la app → Roles → Evaluadores
2. Agregar los Instagram usernames que enviarán DMs de prueba

---

## 5. Levantar el sistema completo

Necesitás 3 terminales abiertas simultáneamente:

### Terminal 1 — Servidor FastAPI

```bash
cd TIF-VB-GIMENEZ/src
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Salida esperada:
```
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Terminal 2 — Túnel ngrok

```bash
ngrok http 8000
```

Salida esperada:
```
Forwarding    https://xxxx-xxx-xxx.ngrok-free.app -> http://localhost:8000
```

Copiar la URL `https://xxxx-xxx-xxx.ngrok-free.app` y usarla en la configuración del webhook de Meta.

### Browser — Dashboard de monitoreo

```
http://localhost:8000/dashboard
```

El dashboard se auto-actualiza cada 30 segundos.

---

## 6. Verificar que todo funciona

### Paso 1 — Health check

```bash
curl http://localhost:8000/health
```
Respuesta esperada:
```json
{"status": "running"}
```

### Paso 2 — Verificar webhook de Meta

En el panel de Meta Developers → Webhooks → hacer clic en "Verificar". Si la configuración es correcta, el campo aparecerá como "Activo".

### Paso 3 — Dashboard vacío

Abrir `http://localhost:8000/dashboard`. Debería mostrar las tarjetas de resumen en 0 y la tabla con "No hay análisis registrados todavía".

### Paso 4 — Enviar DM de prueba

Desde una cuenta configurada como evaluadora, enviar un DM a la cuenta monitoreada. Ejemplos de prueba:

**Mensaje limpio (LOW esperado)**:
```
Hola! Cómo estás?
```

**Mensaje de phishing (HIGH esperado)**:
```
Tu cuenta de Instagram fue suspendida. Verificá tu identidad inmediatamente en: http://instagram-verify.top/login o tu cuenta será eliminada en 24 horas.
```

### Paso 5 — Verificar resultado

1. Ver en la Terminal 1 el log de procesamiento
2. Recargar el dashboard y verificar que aparece la conversación con su nivel de riesgo

---

## 7. Troubleshooting — Errores comunes

### Meta no verifica el webhook ("Error al verificar el token")

**Causa**: ngrok no está corriendo, o la URL en Meta no coincide con la de ngrok, o `META_VERIFY_TOKEN` en `.env` no coincide con el configurado en Meta.

**Solución**: verificar que `uvicorn` está en el puerto 8000, que ngrok expone exactamente ese puerto, y que el token es idéntico en ambos lados (sin espacios).

### `UM_API_KEY not set — IA skipped`

**Causa**: `UM_API_KEY` está vacía en el `.env` o el archivo no fue cargado.

**Solución**: verificar que el `.env` existe en `src/` (no en la raíz del repo), que tiene el formato correcto sin comillas alrededor de los valores, y reiniciar uvicorn.

### `phishtank.csv not found`

**Causa**: el archivo `data/blacklist/phishtank.csv` no existe.

**Efecto**: el sistema sigue funcionando con `blacklist.txt` y URLhaus. Solo se pierde la base de datos PhishTank.

**Solución**: descargar `phishtank.csv` del sitio oficial y colocarlo en `data/blacklist/`.

### `SQLite save_message failed: no such table`

**Causa**: la base de datos no fue inicializada.

**Solución**: ejecutar `python database/init_db.py`.

### El dashboard muestra `—` en todos los campos de análisis

**Causa**: hay mensajes en la tabla `mensaje` pero no hay registros en `analisis_conversacion`. El análisis puede haber fallado silenciosamente.

**Solución**: revisar los logs de la Terminal 1 buscando `WARNING` o `ERROR`. Verificar que `UM_API_KEY` es válida y que `ai.cloud.um.edu.ar` responde.

### ngrok cambia de URL en cada reinicio

**Causa**: con cuenta gratuita, el dominio ngrok es efímero.

**Solución**: registrar una cuenta gratuita en ngrok y usar un dominio estático (`ngrok config add-authtoken TU_TOKEN && ngrok http --domain=TU-DOMINIO.ngrok-free.app 8000`). Actualizar la URL del webhook en Meta cada vez que cambie el dominio.

### `json.JSONDecodeError` en logs — análisis omitido

**Causa**: el modelo UM Cloud devolvió una respuesta no-JSON (por ejemplo, texto de explicación antes del JSON).

**Efecto**: el análisis heurístico se mantiene; el análisis de IA se omite para ese mensaje.

**Solución**: es transitorio. El system prompt incluye `"Return ONLY a valid JSON object, no prose, no markdown"` pero con `temperature=0.1` puede ocurrir ocasionalmente. El siguiente mensaje reintentará el análisis IA.
