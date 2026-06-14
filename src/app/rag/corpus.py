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
]
