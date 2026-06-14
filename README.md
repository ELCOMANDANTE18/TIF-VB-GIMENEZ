<div align="center">
  <img src="src/static/logo.png" alt="Link Seguro" width="160"/>

  <h1>Link Seguro</h1>
  <p><strong>Sistema de detección de phishing en Instagram DMs</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white" alt="Python"/>
    <img src="https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
    <img src="https://img.shields.io/badge/IA-gemma4--26b-orange?logo=google&logoColor=white" alt="IA"/>
    <img src="https://img.shields.io/badge/SQLite-aiosqlite-003B57?logo=sqlite&logoColor=white" alt="SQLite"/>
    <img src="https://img.shields.io/badge/Meta-Webhook-1877F2?logo=meta&logoColor=white" alt="Meta"/>
  </p>
  <p>
    <strong>Trabajo Integrador Final 3 — Ingeniería en Informática</strong><br>
    Universidad de Mendoza · 2026<br>
    Autor: Victor Benjamín Giménez · Legajo: 61.174
  </p>
</div>

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
Meta Graph API (Webhook POST /webhook)
     │  HMAC-SHA256 validation
     ▼
FastAPI + Uvicorn
     │  BackgroundTasks (no bloquea a Meta)
     ├──► URLAnalyzer      (PhishTank 29k dominios + URLhaus + Regex)
     ├──► TextAnalyzer     (4 patrones regex ES/EN de ingeniería social)
     ├──► RAG Retriever    (keyword matching sobre 12 fichas de conocimiento)
     └──► UM Cloud AI      (gemma4-26b — MITRE ATT&CK + Cialdini + lifecycle)
               │
               ▼
         SQLite (aiosqlite, raw SQL)
               │
     ┌─────────┴──────────┐
     ▼                    ▼
Dashboard Web         Notificaciones
/dashboard            DM automático al atacante
(multiusuario,        Email HTML al dueño
 análisis + PDF)      de la cuenta
```

### Diagrama de módulos

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI app                             │
│                                                                 │
│  ┌──────────────┐     ┌─────────────────────────────────────┐  │
│  │   Webhook    │────►│         Analysis Pipeline           │  │
│  │  01-webhook  │     │  ┌────────────┐  ┌───────────────┐  │  │
│  │              │     │  │URLAnalyzer │  │ TextAnalyzer  │  │  │
│  │  GET verify  │     │  │ (PhishTank │  │ (4 patrones   │  │  │
│  │  POST events │     │  │  URLhaus)  │  │  regex ES/EN) │  │  │
│  │  HMAC valid  │     │  └─────┬──────┘  └──────┬────────┘  │  │
│  └──────────────┘     │        └────────┬─────────┘          │  │
│                        │    orchestrator │  02-analysis       │  │
│                        │                ▼                     │  │
│  ┌──────────────┐     │  ┌──────────────────────────────┐   │  │
│  │  Dashboard   │     │  │     IA Generativa + RAG       │   │  │
│  │  05-dashboard│     │  │  RAG retriever (12 fichas)    │   │  │
│  │              │     │  │  UM Cloud gemma4-26b          │   │  │
│  │  lista convs │     │  │  MITRE + Cialdini + lifecycle │   │  │
│  │  detalle     │     │  └──────────────┬───────────────┘   │  │
│  │  export PDF  │     │                  │  03-ai            │  │
│  └──────┬───────┘     └──────────────────┼──────────────────┘  │
│         │                                │                      │
│         ▼                                ▼                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Base de datos — SQLite                       │  │
│  │  conversacion │ mensaje │ analisis_conversacion │ usuario │  │
│  │                     04-db                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                                │                      │
│         ▼                                ▼                      │
│  ┌──────────────┐              ┌─────────────────┐             │
│  │   Auth       │              │  Notificaciones │             │
│  │  bcrypt +    │              │  DM automático  │             │
│  │  itsdangerous│              │  Email HTML     │             │
│  │  cookies 8h  │              │   06-notif.     │             │
│  └──────────────┘              └─────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python 3.14 + FastAPI |
| IA Generativa | gemma4-26b via UM Cloud (OpenAI-compatible API) |
| RAG | Keyword matching sobre corpus de 12 fichas (sin embeddings) |
| Detección heurística | PhishTank (29k dominios) + URLhaus + Regex |
| Base de datos | SQLite + aiosqlite (raw SQL, sin ORM) |
| Autenticación | bcrypt + itsdangerous (cookies firmadas, 8h) |
| Notificaciones | Instagram Messages API + SMTP Gmail |
| Exportación | weasyprint 69.0 (HTML → PDF) |
| Túnel público | ngrok |
| API externa | Meta Graph API v25.0 |

---

## Estructura del proyecto

```
TIF-VB-GIMENEZ/
├── src/
│   ├── app/
│   │   ├── ai/              # Cliente UM Cloud + system prompt + RAG
│   │   ├── analysis/        # URLAnalyzer, TextAnalyzer, Orchestrator, Observer
│   │   ├── dashboard/       # Dashboard web + auth + export PDF
│   │   ├── db/              # Cliente SQLite
│   │   ├── models/          # Schemas Pydantic (URLResult, TextResult, AnalysisResult)
│   │   ├── notifications/   # DM automático + email HTML
│   │   ├── rag/             # Corpus de conocimiento + retriever
│   │   ├── utils/           # Logger
│   │   └── webhook/         # Endpoints Meta Webhook + validación HMAC
│   ├── database/            # Schema SQL + script de inicialización
│   ├── data/                # BD SQLite local (excluida del repo)
│   ├── docs/                # Documentación técnica (ver abajo)
│   ├── scripts/             # Scripts de setup, evaluación y mantenimiento
│   ├── static/              # Logo + assets estáticos
│   └── tests/               # Dataset de evaluación (12 casos etiquetados)
├── docs/                    # Índice de documentación (ver abajo)
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

Para más detalle: [docs/INSTALACION.md](docs/INSTALACION.md)

---

## Usuarios de demo

| Usuario | Contraseña | Rol |
|---|---|---|
| admin | admin123 | Ve el análisis completo; mensajes protegidos |
| flia_test | link2024 | Ve sus conversaciones con texto completo |
| benja | link2024 | Ve sus conversaciones con texto completo |
| hernesto | link2024 | Ve sus conversaciones con texto completo |

---

## Documentación del proyecto

### Documentación técnica general

| Documento | Contenido |
|---|---|
| [Arquitectura](docs/README_TECNICO.md) | Arquitectura completa, componentes y flujos |
| [Decisiones de arquitectura (ADRs)](docs/DECISIONES_ARQUITECTURA.md) | Registro de decisiones técnicas con justificación |
| [Base de datos](docs/BASE_DE_DATOS.md) | Modelo de datos SQLite, schema y queries clave |
| [Sustento del prompt de IA](docs/PROMPT_SUSTENTO.md) | Marco teórico: MITRE ATT&CK, Cialdini, APWG |
| [Instalación](docs/INSTALACION.md) | Guía paso a paso con prerequisitos y troubleshooting |
| [Auditoría del repositorio](docs/AUDITORIA_REPO.md) | Auditoría completa, métricas de evaluación y mejoras propuestas |

### Documentación por módulo

| Módulo | Archivo | Descripción |
|---|---|---|
| Webhook | [docs/modulos/01-webhook.md](docs/modulos/01-webhook.md) | Recepción de eventos Meta, HMAC, BackgroundTasks |
| Motor de análisis | [docs/modulos/02-analysis.md](docs/modulos/02-analysis.md) | Pipeline: URL + Text + URLhaus + Orchestrator + Observer |
| IA Generativa | [docs/modulos/03-ai.md](docs/modulos/03-ai.md) | UM Cloud (gemma4-26b), prompts, RAG |
| Base de datos | [docs/modulos/04-db.md](docs/modulos/04-db.md) | SQLite schema, funciones, decisiones de diseño |
| Dashboard | [docs/modulos/05-dashboard.md](docs/modulos/05-dashboard.md) | UI web, auth, export PDF |
| Notificaciones | [docs/modulos/06-notifications.md](docs/modulos/06-notifications.md) | DM automático Instagram + email HTML |

---

## Métricas de evaluación (dataset 12 casos)

| Clase | Precision | Recall | F1 |
|---|---|---|---|
| LOW | 100% | 50% | 66.67% |
| MEDIUM | 100% | 60% | 75.00% |
| HIGH | 62.5% | 100% | 76.92% |
| **Macro** | **87.5%** | **70%** | **72.86%** |

Score global: **9/12 (75%)**. Ver [docs/AUDITORIA_REPO.md](docs/AUDITORIA_REPO.md) PARTE 7 para análisis completo.

---

## Estándares aplicados

- **MITRE ATT&CK T1566** — Clasificación de técnicas de phishing (T1566.002 Spearphishing Link, T1566.003 via Service)
- **APWG eCrime Reports** — Taxonomía de ataques en redes sociales
- **Principios de Cialdini** — Mecanismos psicológicos de ingeniería social (autoridad, urgencia, escasez, prueba social, simpatía, compromiso)
