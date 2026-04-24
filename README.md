# Proyecto Link Seguro - TIF III

### Este es el repositorio oficial de mi Trabajo Integrador Final. Acá voy a ir subiendo todo lo que vaya haciendo durante el semestre para que esté todo en un mismo lugar.


# Link Seguro — Detección de Phishing en Instagram DMs

## Requisitos
- Python 3.10+
- ngrok

## Instalación

```bash
# 1. Clonar el repo
git clone <url-del-repo>
cd TIF-VB-GIMENEZ/src

# 2. Setup automático
bash setup.sh

# 3. Completar credenciales
nano .env
```

## Uso

**Terminal 1 — Servidor:**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Túnel público:**
```bash
ngrok http 8000
```

**Verificar que funciona:**
```
http://localhost:8000/health
http://localhost:8000/docs
http://127.0.0.1:4040  ← inspector ngrok
```

## Registrar Webhook en Meta

1. Ir a `developers.facebook.com` → `api_tester` → Instagram → Configuración de la API
2. Pegar la URL de ngrok + `/webhook`
3. Pegar el `META_VERIFY_TOKEN` del `.env`
4. Click en Guardar

## Variables de entorno necesarias (.env)

```env
FACEBOOK_PAGE_ID=
META_APP_ID=
META_APP_SECRET=
META_VERIFY_TOKEN=
PAGE_ACCESS_TOKEN=
```
