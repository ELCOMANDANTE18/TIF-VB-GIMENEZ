"""
Base de conocimiento para el retriever. Cada entrada tiene:
  - id: identificador único
  - title: título legible
  - keywords: términos que disparan esta ficha (se buscan en mensaje + reasons + patterns)
  - content: texto que se inyecta en el prompt cuando la ficha es relevante
"""

CORPUS: list[dict] = [
    # ── CATEGORÍAS DE ATAQUE ──────────────────────────────────────────────────
    {
        "id": "account_verification_scam",
        "title": "Estafa de verificación de cuenta (Account Verification Scam)",
        "keywords": [
            "support_impersonation", "verificar", "verificación", "verify",
            "cuenta suspendida", "suspendida", "suspended", "bloqueada",
            "equipo de soporte", "support team", "instagram support",
            "urgency", "urgente", "24 horas", "within 24",
            "typosquatting", "login", "secure", "badge", "copyright",
            # variantes rioplatenses
            "tu perfil va a ser dado de baja", "detectamos movimientos extraños",
            "el equipo de seguridad de Meta", "tu cuenta va a quedar inhabilitada",
        ],
        "content": (
            "DESCRIPCIÓN: El atacante se hace pasar por el equipo de soporte de Instagram "
            "o Meta. Alega que la cuenta fue reportada, viola términos, o tiene actividad "
            "inusual, y exige verificación urgente mediante un link externo.\n"
            "INDICADORES CLAVE: impersonación de soporte oficial, urgencia extrema (24-48hs), "
            "amenaza de suspensión/eliminación permanente, link con dominio que imita Instagram "
            "(instagram-verify.com, seguridad-ig.com, etc.), solicitud de credenciales o datos.\n"
            "DIFERENCIADOR: Instagram NUNCA contacta por DM para pedir verificación. Cualquier "
            "mensaje que diga ser de Instagram y pida hacer clic en un link es falso.\n"
            "FASE TÍPICA: hook → pressure. MITRE: T1566.002."
        ),
    },
    {
        "id": "credential_harvesting",
        "title": "Robo de credenciales (Credential Harvesting)",
        "keywords": [
            "credential_request", "contraseña", "password", "usuario", "user",
            "pin", "credenciales", "credentials", "ingresar", "enter",
            "formulario", "form", "login", "iniciar sesión",
        ],
        "content": (
            "DESCRIPCIÓN: El atacante solicita directamente contraseñas, PINs, códigos "
            "de recuperación u otras credenciales, ya sea en el mensaje o a través de "
            "un formulario en un sitio falso.\n"
            "INDICADORES CLAVE: solicitud explícita de password/PIN/usuario, link a página "
            "de login falsa que imita Instagram/Meta, frase como 'ingresá tus datos', "
            "'completá el formulario', 'confirmá tu contraseña'.\n"
            "DIFERENCIADOR: puede combinarse con account_verification_scam (usan el pretexto "
            "de verificación para obtener credenciales). La diferencia es que aquí el robo "
            "de credencial es el objetivo explícito, no solo el medio.\n"
            "FASE TÍPICA: hook → pressure. MITRE: T1566.002 / T1598."
        ),
    },
    {
        "id": "otp_request",
        "title": "Solicitud de código OTP / 2FA",
        "keywords": [
            "otp", "código", "code", "verificación", "verification code",
            "sms", "autenticación", "authentication", "token", "6 dígitos",
            "recibiste un código", "te llegó un código", "mandame el código",
            "two factor", "2fa", "doble factor",
            # variantes rioplatenses
            "me llegó un código a tu número", "necesito que me reenvíes ese mensaje",
            "es solo 6 números", "pasame el código que te llegó",
        ],
        "content": (
            "DESCRIPCIÓN: El atacante pide el código de verificación de dos factores (OTP/2FA) "
            "que Instagram envía por SMS. Con ese código toma control inmediato de la cuenta.\n"
            "INDICADORES CLAVE: mención de 'código', 'SMS', '6 dígitos', 'te llegó un mensaje', "
            "pretexto de 'te lo mandé por error', 'necesito que me lo reenvíes', urgencia alta.\n"
            "DIFERENCIADOR: es el ataque más directo — con el OTP el atacante entra en segundos. "
            "Nadie legítimo pide nunca el código 2FA. Es señal de HIGH risk inmediato.\n"
            "FASE TÍPICA: hook (acción directa). MITRE: T1566.003."
        ),
    },
    {
        "id": "fake_giveaway",
        "title": "Sorteo / regalo falso (Fake Giveaway)",
        "keywords": [
            "fraudulent_offer", "ganaste", "winner", "ganador", "premio",
            "prize", "sorteo", "giveaway", "gratis", "free", "regalo",
            "gift", "reclama", "claim", "recompensa", "reward",
            "gift card", "tarjeta regalo", "voucher",
            # variantes rioplatenses
            "fuiste el elegido", "te tocó a vos",
            "mandanos tus datos para coordinar", "ganaste sin participar",
        ],
        "content": (
            "DESCRIPCIÓN: El atacante informa a la víctima que 'ganó' un sorteo, premio o "
            "regalo y la dirige a un link para 'reclamarlo'. El objetivo es robar datos "
            "personales, credenciales, o dinero (costo de envío).\n"
            "INDICADORES CLAVE: notificación de premio no solicitada, urgencia ('tenés 24hs "
            "para reclamar'), link externo para 'verificar identidad', solicitud de datos "
            "personales o pago de envío.\n"
            "DIFERENCIADOR: el pretexto del premio distingue este ataque de account_verification_scam. "
            "Frecuentemente suplanta marcas conocidas (Nike, Apple, Samsung, Instagram mismo).\n"
            "PRINCIPIOS CIALDINI: reciprocidad (el regalo), urgencia/escasez (tiempo limitado).\n"
            "FASE TÍPICA: hook. MITRE: T1566.002."
        ),
    },
    {
        "id": "pig_butchering",
        "title": "Estafa de inversión / pig butchering",
        "keywords": [
            "inversión", "investment", "cripto", "crypto", "bitcoin", "ethereum",
            "trading", "plataforma", "rentabilidad", "ganancias", "profits",
            "te enseño", "te ayudo a invertir", "oportunidad", "opportunity",
            "rendimiento", "return", "retorno", "porcentaje", "percentage",
            # variantes rioplatenses / culturales
            "tengo una plataforma exclusiva", "empezá con lo que puedas",
            "te paso el link de la app", "tengo un grupito donde compartimos señales",
            "te enseño a hacer trading",
        ],
        "content": (
            "DESCRIPCIÓN: Estafa de larga duración. El atacante construye confianza durante "
            "días o semanas (fase approach/bond), luego presenta una 'oportunidad de inversión' "
            "en cripto u otros activos. La víctima deposita dinero real que nunca puede retirar.\n"
            "INDICADORES CLAVE: conversación inicial casual y afectuosa sin solicitudes, "
            "mención gradual de inversiones/cripto, promesas de altas ganancias con bajo riesgo, "
            "plataforma de inversión desconocida, pedido de depósito inicial pequeño (para generar confianza).\n"
            "DIFERENCIADOR: la fase temprana (approach) parece conversación normal — esto es intencional. "
            "Un mensaje de 'hola, te vi en Instagram y me parecés interesante' de un desconocido "
            "seguido de cualquier mención de dinero/cripto es señal de alerta.\n"
            "PRINCIPIOS CIALDINI: liking (crear vínculo afectivo), autoridad (experto en trading), "
            "prueba social (mostrar ganancias falsas), compromiso (pequeños depósitos progresivos).\n"
            "FASE TÍPICA: approach → bond → hook. MITRE: T1566.003."
        ),
    },
    {
        "id": "brand_support_impersonation",
        "title": "Suplantación de marca o soporte (Brand Impersonation)",
        "keywords": [
            "support_impersonation", "oficial", "official", "verificado", "verified",
            "meta", "instagram", "facebook", "marca", "brand", "copyright",
            "derechos de autor", "infracción", "violation", "política", "policy",
            "equipo", "team", "help desk",
        ],
        "content": (
            "DESCRIPCIÓN: El atacante se hace pasar por representante oficial de Instagram, "
            "Meta, o una marca conocida. Puede usar perfil falso con logo, nombre similar "
            "al oficial, o simplemente afirmar ser del equipo en el texto.\n"
            "INDICADORES CLAVE: perfil sin historial o muy nuevo, nombre como 'Instagram.Support', "
            "claim de 'somos el equipo oficial', referencia a violación de política o copyright, "
            "pedido de acción inmediata para 'resolver' un problema inventado.\n"
            "DIFERENCIADOR respecto a account_verification_scam: en brand_support_impersonation "
            "el foco es la impersonación de la marca en sí (puede no pedir credenciales directamente, "
            "sino datos personales o pago para 'verificar' la cuenta).\n"
            "FASE TÍPICA: hook → pressure. MITRE: T1566.002."
        ),
    },
    {
        "id": "romance_scam",
        "title": "Estafa romántica (Romance Scam)",
        "keywords": [
            "amor", "love", "novio", "novia", "relación", "relationship",
            "te quiero", "enamorado", "enamorada", "pareja", "couple",
            "nos conocemos", "me gustás", "atractivo", "attractive",
            "videollamada", "video call", "foto", "photo", "conocerte",
        ],
        "content": (
            "DESCRIPCIÓN: El atacante construye una relación romántica o de amistad con la "
            "víctima durante un período prolongado. Una vez establecido el vínculo, solicita "
            "dinero por una 'emergencia', pide datos, o introduce una estafa de inversión.\n"
            "INDICADORES CLAVE: contacto inicial no solicitado con elogios ('sos muy atractivo/a'), "
            "perfil con pocas fotos o fotos de modelo/militar/profesional exitoso, resistencia "
            "a videollamadas en vivo (siempre tienen excusas), solicitud de dinero por emergencia.\n"
            "DIFERENCIADOR respecto a pig_butchering: romance_scam tiene foco en la relación "
            "emocional; pig_butchering tiene foco en la inversión. Pueden superponerse.\n"
            "PRINCIPIOS CIALDINI: liking (vínculo afectivo), reciprocidad (atención/afecto).\n"
            "FASE TÍPICA: approach → bond → hook. MITRE: T1566.003."
        ),
    },

    # ── TÉCNICAS MITRE ────────────────────────────────────────────────────────
    {
        "id": "mitre_T1566_002",
        "title": "MITRE T1566.002 — Spearphishing Link",
        "keywords": [
            "link", "enlace", "url", "hacé clic", "click here", "visitá",
            "typosquatting", "suspicious TLD", "shortener", "bit.ly", "tinyurl",
            "verify", "secure", "login", "portal",
        ],
        "content": (
            "TÉCNICA T1566.002: el atacante envía un link malicioso diseñado para llevar "
            "a la víctima a un sitio falso de captura de credenciales o descarga de malware.\n"
            "SEÑALES EN DMs: URL con dominio que imita la plataforma legítima (instagram-verify.com, "
            "meta-soporte.com), acortadores de URL (bit.ly, cutt.ly), dominios con TLDs inusuales "
            "(.top .xyz .cyou .click), subdominos como instagram.login-secure.com.\n"
            "CONTEXTO: Instagram y Meta NUNCA envían links de verificación por DM. Cualquier "
            "link en un DM no solicitado de un desconocido es potencialmente malicioso."
        ),
    },
    {
        "id": "mitre_T1566_003",
        "title": "MITRE T1566.003 — Spearphishing via Service",
        "keywords": [
            "instagram", "dm", "mensaje directo", "plataforma", "red social",
            "pig_butchering", "otp", "romance", "cripto", "crypto",
        ],
        "content": (
            "TÉCNICA T1566.003: el atacante usa la propia plataforma de mensajería (Instagram DM) "
            "como vector de ataque, sin necesidad de un link externo. El canal legítimo es el vector.\n"
            "SEÑALES EN DMs: solicitud de OTP/2FA directamente por DM, construcción de confianza "
            "dentro de la plataforma antes de introducir el ataque (pig butchering, romance scam), "
            "manipulación sin links (el objetivo es extraer información o dinero via el propio chat).\n"
            "CONTEXTO: más difícil de detectar heurísticamente porque no hay URL. Requiere análisis "
            "de patrones conversacionales y contexto acumulado."
        ),
    },

    # ── PRINCIPIOS DE CIALDINI ────────────────────────────────────────────────
    {
        "id": "cialdini_urgency_scarcity",
        "title": "Cialdini: Urgencia y Escasez en phishing",
        "keywords": [
            "urgency", "urgente", "inmediatamente", "24 horas", "48 horas",
            "expire", "vence", "último aviso", "final notice", "act now",
            "ahora mismo", "de inmediato", "tiempo limitado", "limited time",
            "suspendida", "eliminada", "permanentemente",
        ],
        "content": (
            "PRINCIPIO — URGENCIA/ESCASEZ: el atacante crea presión temporal artificial para "
            "que la víctima actúe sin pensar. Frases típicas en español: 'tenés 24 horas', "
            "'tu cuenta será eliminada permanentemente', 'último aviso', 'actuá ya', "
            "'tiempo limitado para reclamar'.\n"
            "FUNCIÓN EN EL ATAQUE: impide que la víctima consulte con otros o verifique la "
            "legitimidad del mensaje. Cuanto más urgente suena el mensaje, más probable es "
            "que sea una estafa — las plataformas legítimas dan tiempo razonable para actuar.\n"
            "DETECCIÓN: buscar deadlines específicos, amenazas de consecuencias irreversibles, "
            "palabras como 'inmediatamente', 'ahora mismo', 'sin demora'."
        ),
    },
    {
        "id": "cialdini_authority",
        "title": "Cialdini: Autoridad en phishing",
        "keywords": [
            "support_impersonation", "autoridad", "authority", "oficial", "official",
            "equipo", "team", "soporte", "support", "verificado", "verified",
            "experto", "expert", "asesor", "advisor", "instagram", "meta",
        ],
        "content": (
            "PRINCIPIO — AUTORIDAD: el atacante se presenta como figura de autoridad legítima "
            "(soporte de Instagram, equipo de seguridad de Meta, experto financiero, militar, médico) "
            "para generar confianza y reducir el pensamiento crítico de la víctima.\n"
            "FUNCIÓN EN EL ATAQUE: la víctima es menos propensa a cuestionar solicitudes inusuales "
            "cuando cree que vienen de una autoridad reconocida.\n"
            "SEÑALES: afirmaciones de ser 'oficial', 'verificado', uso de logos en perfil, "
            "lenguaje técnico/formal, referencias a 'políticas' o 'procedimientos de seguridad'.\n"
            "NOTA: Instagram y Meta no contactan usuarios por DM. Cualquier perfil que afirme "
            "ser del equipo de Instagram debe considerarse sospechoso."
        ),
    },

    # ── CALIBRACIÓN DE SEVERIDAD ──────────────────────────────────────────────
    {
        "id": "severity_calibration",
        "title": "Calibración de severidad: cuándo usar MEDIUM vs HIGH",
        "keywords": [
            # Patrones de texto detectados por TextAnalyzer
            "support_impersonation", "fraudulent_offer", "urgency",
            # Patrones de URL detectados por URLAnalyzer
            "shortener", "cutt.ly", "bit.ly", "tinyurl", "acortador",
            # Palabras del mensaje que identifican ataques en fase temprana
            "equipo de soporte", "actividad inusual", "inusual", "restricciones",
            "ganaste", "ganador", "sorteo", "premio", "48 horas", "a la brevedad",
            "vence", "confirmanos", "confirmar identidad", "titular",
            "sos el titular", "somos del equipo", "somos el equipo",
        ],
        "content": (
            "REGLA DE CALIBRACIÓN DE SEVERIDAD — aplicar ANTES de asignar HIGH:\n\n"
            "MEDIUM (usar cuando hay 2+ indicadores pero FALTA el pedido explícito):\n"
            "• Suplantación de soporte + urgencia, pero SIN link externo ni pedido de "
            "contraseña/OTP/código → MEDIUM\n"
            "• Link acortado (bit.ly, cutt.ly) enviado por desconocido, sin formulario "
            "de login ni solicitud de datos → MEDIUM\n"
            "• Sorteo o premio anunciado sin link de reclamo ni solicitud de datos "
            "personales o pago → MEDIUM\n"
            "• Contacto no solicitado con pretexto de inversión o romance, sin "
            "solicitud directa de dinero ni link a plataforma → MEDIUM\n\n"
            "HIGH (requiere al menos UNO de los siguientes):\n"
            "• Link externo + formulario de login o solicitud de credenciales/OTP\n"
            "• Pedido explícito de contraseña, código SMS de 6 dígitos, o datos de tarjeta\n"
            "• Dominio de phishing confirmado (typosquatting, TLD .xyz/.top/.click)\n"
            "• Solicitud directa de transferencia de dinero o criptomonedas\n\n"
            "PRINCIPIO: la presencia de indicadores de ataque sin el 'trigger' de acción "
            "comprometedora indica que el atacante aún está en fase approach/hook temprana. "
            "Clasificar como MEDIUM permite monitorear sin generar falsas alarmas que "
            "saturen al analista."
        ),
    },

    # ── MARCOS NORMATIVOS ─────────────────────────────────────────────────────
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
]
