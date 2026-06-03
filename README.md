# 🛡️ Link Seguro
### Sistema de detección de phishing en Instagram DMs
**Trabajo Integrador Final — Ingeniería en Sistemas**  
Universidad de Mendoza — 2026  
Autor: Victor Benjamín Giménez

---

## ¿Qué hace?

Link Seguro monitorea los mensajes directos (DMs) de Instagram 
en tiempo real y detecta intentos de phishing mediante un 
pipeline de análisis de 4 capas.

---

## Arquitectura

```
Instagram DM
     │
     ▼
Meta Graph API (Webhook)
     │
     ▼
FastAPI + Uvicorn
     │
     ├──► URLAnalyzer      (PhishTank 29k dominios + URLhaus + Regex)
     ├──► TextAnalyzer     (Patrones de ingeniería social)
     └──► UM Cloud AI      (gemma4-26b — MITRE ATT&CK + APWG + Cialdini)
               │
               ▼
         SQLite (local)
               │
               ▼
    Dashboard Web /dashboard
    (login multiusuario, alertas, detalle por conversación)
```

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python 3.14 + FastAPI |
| IA Generativa | gemma4-26b via UM Cloud |
| Detección heurística | PhishTank + URLhaus + Regex |
| Base de datos | SQLite + aiosqlite |
| Autenticación | bcrypt + itsdangerous |
| Túnel público | ngrok |
| API externa | Meta Graph API v25.0 |

---

## Estructura del proyecto

```
TIF-VB-GIMENEZ/
├── src/
│   ├── app/
│   │   ├── ai/              # Cliente UM Cloud + system prompt
│   │   ├── analysis/        # URLAnalyzer, TextAnalyzer, Orchestrator
│   │   ├── dashboard/       # Dashboard web + autenticación
│   │   ├── db/              # Cliente SQLite
│   │   ├── notifications/   # Módulo de alertas Instagram
│   │   └── webhook/         # Endpoints Meta Webhook
│   ├── database/            # Schema SQL + script de inicialización
│   ├── data/                # BD SQLite local (no se sube al repo)
│   ├── docs/                # Documentación técnica
│   ├── scripts/             # Scripts de setup y mantenimiento
│   └── tests/               # Dataset de evaluación
├── .gitignore
└── README.md
```

---

## Instalación rápida

```bash
cd src
bash setup.sh
nano .env          # completar credenciales
python database/init_db.py
python scripts/setup_usuarios.py
uvicorn app.main:app --reload --port 8000
```

Ver: http://localhost:8000/dashboard  
Login: admin / admin123

---

## Documentación técnica

| Documento | Contenido |
|---|---|
| docs/README_TECNICO.md | Arquitectura completa |
| docs/PROMPT_SUSTENTO.md | Sustento académico de la IA |
| docs/BASE_DE_DATOS.md | Modelo de datos SQLite |
| docs/DECISIONES_ARQUITECTURA.md | Registro de decisiones (ADRs) |
| docs/INSTALACION.md | Guía paso a paso |

---

## Usuarios de demo

| Usuario | Contraseña | Rol |
|---|---|---|
| admin | admin123 | Ve todo |
| flia_test | link2024 | Ve sus conversaciones |
| benja | link2024 | Ve sus conversaciones |
| hernesto | link2024 | Ve sus conversaciones |

---

## Estándares aplicados

- **MITRE ATT&CK T1566** — Clasificación de técnicas de phishing
- **APWG eCrime Reports** — Taxonomía de ataques en redes sociales  
- **Principios de Cialdini** — Mecanismos psicológicos de ingeniería social
