CREATE TABLE IF NOT EXISTS conversacion (
    id_conversacion         TEXT PRIMARY KEY,
    ig_conversation_id      TEXT,
    cuenta_monitoreada      TEXT NOT NULL,
    participante_id         TEXT NOT NULL,
    participante_username   TEXT,
    risk_level_actual       TEXT DEFAULT 'LOW' CHECK(risk_level_actual IN ('LOW','MEDIUM','HIGH')),
    risk_level_conversacion TEXT DEFAULT 'LOW' CHECK(risk_level_conversacion IN ('LOW','MEDIUM','HIGH')),
    total_mensajes          INTEGER DEFAULT 0,
    primer_mensaje_at       DATETIME,
    ultimo_mensaje_at       DATETIME,
    observado_at            DATETIME,
    creada_at               DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensaje (
    id_mensaje          TEXT PRIMARY KEY,
    id_conversacion     TEXT NOT NULL REFERENCES conversacion(id_conversacion),
    sender_id           TEXT NOT NULL,
    es_entrante         BOOLEAN NOT NULL DEFAULT 1,
    texto               TEXT,
    urls_detectadas     TEXT DEFAULT '[]',
    timestamp_ig        INTEGER,
    recibido_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analisis_conversacion (
    id_analisis             INTEGER PRIMARY KEY AUTOINCREMENT,
    id_conversacion         TEXT NOT NULL REFERENCES conversacion(id_conversacion),
    id_mensaje_disparador   TEXT NOT NULL REFERENCES mensaje(id_mensaje),
    mensajes_analizados     INTEGER DEFAULT 0,
    score_urls              REAL DEFAULT 0.0,
    score_texto             REAL DEFAULT 0.0,
    score_ia                REAL DEFAULT 0.0,
    score_final             REAL DEFAULT 0.0,
    risk_level              TEXT CHECK(risk_level IN ('LOW','MEDIUM','HIGH')),
    categoria_ataque        TEXT DEFAULT 'none',
    tecnica_mitre           TEXT DEFAULT 'none',
    principios_cialdini     TEXT DEFAULT '[]',
    etapa_lifecycle         TEXT DEFAULT 'n/a',
    urls_sospechosas        TEXT DEFAULT '[]',
    accion_recomendada      TEXT DEFAULT 'allow',
    explicacion_usuario     TEXT,
    explicacion_analista    TEXT,
    analizado_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mensaje_conversacion
    ON mensaje(id_conversacion);
CREATE INDEX IF NOT EXISTS idx_analisis_conversacion
    ON analisis_conversacion(id_conversacion);
CREATE INDEX IF NOT EXISTS idx_analisis_risk
    ON analisis_conversacion(risk_level);
CREATE INDEX IF NOT EXISTS idx_conversacion_risk
    ON conversacion(risk_level_actual);
