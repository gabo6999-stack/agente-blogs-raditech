import os
from dotenv import load_dotenv

load_dotenv()

SITES = {
    "raditech": {
        "wp_url": os.getenv("SITE1_WP_URL"),
        "wp_user": os.getenv("SITE1_WP_USER"),
        "wp_password": os.getenv("SITE1_WP_PASSWORD"),
        "category": "Tecnología Médica",
        "niche": "software médico, sistemas PACS-RIS, teleradiología y gestión hospitalaria en México",
        "language": "es",
        "keywords_seed": [
            "PACS México", "sistema PACS hospital", "teleradiología",
            "RIS radiología", "HIS hospital", "imágenes médicas digitales",
            "DICOM viewer", "radiología digital", "software médico hospital",
            "gestión de estudios radiológicos", "VIRA PACS", "teleradiología 24/7",
            "sistema de información hospitalaria", "radiología a distancia",
            "expediente clínico electrónico", "interoperabilidad HL7 FHIR",
            "inteligencia artificial radiología", "workstation radiología",
            "monitor médico diagnóstico", "seguridad informática salud",
        ],
        "publish_days": ["monday", "tuesday", "thursday", "friday"],
        "publish_time": "09:00",
        "post_length": 1800,
        "unsplash_fallback": "hospital radiology technology medical imaging",
    },
    "tnrvisual": {
        "wp_url": os.getenv("SITE2_WP_URL"),
        "wp_user": os.getenv("SITE2_WP_USER"),
        "wp_password": os.getenv("SITE2_WP_PASSWORD"),
        "category": "Marketing Digital",
        "niche": "marketing digital, publicidad online, SEO, redes sociales, branding y desarrollo web para PyMEs y negocios en México",
        "language": "es",
        "keywords_seed": [
            "agencia de marketing digital", "marketing digital para pymes", "meta ads",
            "google ads", "tiktok ads", "publicidad en redes sociales", "posicionamiento SEO",
            "SEO local", "embudo de ventas", "community manager", "estrategia de redes sociales",
            "diseño de páginas web", "branding para empresas", "email marketing",
            "cómo generar leads", "marketing de contenidos", "reputación online",
            "Google My Business", "campañas de publicidad", "automatización de marketing",
        ],
        "publish_days": ["saturday"],
        "publish_time": "09:00",
        "post_length": 1700,
        "unsplash_fallback": "digital marketing team office laptop",
        "prompt_profile": {
            "brand": "TNR Relieve Visual",
            "audience": "dueños de PyME, emprendedores y responsables de marketing de negocios en México que quieren atraer más clientes y vender más",
            "objective": (
                "capturar tráfico orgánico de negocios que buscan crecer con marketing digital "
                "(publicidad, SEO, redes sociales, desarrollo web) y posicionar a TNR Relieve Visual "
                "como una agencia experta, cercana y orientada a resultados"
            ),
            "tone": (
                "profesional pero accesible y práctico, orientado a ventas y ROI, en español de México; "
                "explica en simple, sin jerga innecesaria, con ejemplos aplicables a PyMEs mexicanas"
            ),
            "angles": [
                "cómo generar más clientes/leads con una táctica concreta",
                "guías prácticas paso a paso para dueños de negocio",
                "errores comunes en publicidad/SEO/redes y cómo evitarlos",
                "comparativas útiles (p. ej. Meta Ads vs Google Ads)",
                "cuánto cuesta / cómo presupuestar una campaña o servicio",
                "cómo medir resultados y ROI en marketing",
                "tendencias de marketing digital en México",
            ],
            "categories": {
                "Marketing Digital": "estrategia, embudos, growth y tendencias generales de marketing",
                "Publicidad y Ads": "Google Ads, Meta Ads (Facebook/Instagram), TikTok Ads y campañas de pago",
                "SEO": "posicionamiento orgánico, SEO local, keywords, contenido y SEO técnico",
                "Redes Sociales": "community management, contenido, calendario y engagement",
                "Desarrollo Web": "diseño y desarrollo de sitios que venden, landing pages y e-commerce",
                "Branding": "identidad de marca, naming, logotipo y reputación",
            },
            "cta": "cierre con un CTA sutil a cotizar sin costo o escribir por WhatsApp a TNR Relieve Visual",
            "internal_links": {
                "https://tnrvisual.com/publicidad-en-redes-sociales/": "Publicidad en redes sociales (Meta + TikTok Ads)",
                "https://tnrvisual.com/campanas-de-meta-ads/": "Campañas de Meta Ads (Facebook e Instagram)",
                "https://tnrvisual.com/campanas-de-tiktok-ads/": "Campañas de TikTok Ads",
                "https://tnrvisual.com/campanas-de-google-ads/": "Campañas de Google Ads",
                "https://tnrvisual.com/posicionamiento-seo/": "Posicionamiento SEO",
                "https://tnrvisual.com/diseno-de-paginas-web/": "Diseño de páginas web",
                "https://tnrvisual.com/agencia-de-branding/": "Branding y diseño de marca",
                "https://tnrvisual.com/diseno-grafico/": "Diseño gráfico",
                "https://tnrvisual.com/redes-sociales-para-empresas/": "Manejo de redes sociales / community manager",
                "https://tnrvisual.com/desarrollo-de-software-a-la-medida/": "Desarrollo de software a la medida (CRM, ERP)",
                "https://tnrvisual.com/productora-audiovisual-cdmx/": "Producción audiovisual (foto y video)",
                "https://tnrvisual.com/chatbot-para-whatsapp/": "Chatbot y automatización para WhatsApp",
                "https://tnrvisual.com/contacto/": "Contacto / cotización sin costo",
            },
        },
    },
    "cmlc": {
        "wp_url": os.getenv("SITE3_WP_URL"),
        "wp_user": os.getenv("SITE3_WP_USER"),
        "wp_password": os.getenv("SITE3_WP_PASSWORD"),
        "category": "Radiología e Imagen",
        "niche": "radiología e imagenología diagnóstica para pacientes (rayos X, tomografía, ultrasonido, mastografía) en Mazatlán, Sinaloa",
        "language": "es",
        "keywords_seed": [
            "historia de la radiología", "rayos x Mazatlán", "tomografía Mazatlán",
            "estudios de imagen Mazatlán", "ultrasonido Mazatlán", "mastografía Mazatlán",
            "rayos x a domicilio", "preparación para tomografía", "qué es una densitometría ósea",
            "radiología e imagen", "panorámica dental Mazatlán", "electrocardiograma Mazatlán",
        ],
        "publish_days": ["wednesday"],
        "publish_time": "10:00",
        "post_length": 1300,
        "unsplash_fallback": "vintage x-ray machine radiology history",
        "prompt_profile": {
            "brand": "Centro Médico Las Conchas",
            "audience": (
                "pacientes y público general en Mazatlán y la región que necesitan estudios de "
                "radiología e imagen (rayos X, tomografía, ultrasonido, mastografía, densitometría) "
                "por indicación médica o revisión preventiva, sin conocimientos técnicos de medicina"
            ),
            "objective": (
                "generar contenido de divulgación confiable sobre radiología e imagenología diagnóstica "
                "que eduque al paciente, reduzca su ansiedad ante los estudios, y posicione al Centro "
                "Médico Las Conchas (gabinete del Dr. Pedro Gavito) como la opción de confianza en "
                "Mazatlán para agendar su estudio"
            ),
            "tone": (
                "cercano, cálido y claro, como lo explicaría el propio médico al paciente; sin "
                "tecnicismos innecesarios (o explicados en cuanto se usan), en español de México; "
                "empático, nunca alarmista"
            ),
            "angles": [
                "historia y evolución de la radiología y las técnicas de imagen",
                "qué esperar en un estudio específico (rayos X, tomografía, ultrasonido, mastografía) paso a paso",
                "cómo prepararse antes de un estudio (ayuno, ropa, indicaciones)",
                "diferencias entre modalidades de imagen y cuándo el médico pide cada una",
                "mitos y verdades sobre la radiación en estudios de imagen",
                "densitometría ósea y mastografía: por qué son clave en la prevención",
                "servicio de rayos X a domicilio: para quién es y cómo funciona",
            ],
            "categories": {
                "Radiología e Imagen": (
                    "todo el contenido de divulgación sobre estudios de radiología e imagenología "
                    "diagnóstica del Centro Médico Las Conchas"
                ),
            },
            "cta": (
                "cierre invitando a agendar su estudio llamando al 669 990 2288 / 669 269 6255 o "
                "visitando el Centro Médico Las Conchas en Plaza Las Conchas, Mazatlán"
            ),
            "internal_links": {
                "https://centromedicolasconchas.com/": "Agenda tu estudio en Centro Médico Las Conchas",
                "https://centromedicolasconchas.com/#servicios": "Estudios de radiología e imagen que realizamos",
                "https://centromedicolasconchas.com/#tomografia": "Tomografía multicorte y reconstrucción 3D",
                "https://centromedicolasconchas.com/#nosotros": "Conoce al Dr. Pedro Gavito y el Centro Médico Las Conchas",
                "https://centromedicolasconchas.com/#ubicacion": "Ubicación y cómo llegar a Plaza Las Conchas",
            },
        },
    },
    "propertyledger": {
        "wp_url": os.getenv("SITE4_WP_URL"),
        "wp_user": os.getenv("SITE4_WP_USER"),
        "wp_password": os.getenv("SITE4_WP_PASSWORD"),
        "category": "Property Management Accounting",
        "niche": "outsourced accounting for property management companies, HOAs, condo associations and real estate investors in South Florida",
        "language": "en",
        "keywords_seed": [
            "property management accounting", "trust accounting for property managers",
            "HOA accounting", "condo association accounting",
            "outsourced accounting for property managers", "property management bookkeeping",
            "owner statements property management", "month end close checklist property management",
            "trust account reconciliation", "HOA financial reporting",
            "property management CPA", "reserve study HOA", "AppFolio accounting",
            "Buildium accounting", "South Florida property management accounting",
            "commingling of funds property management", "property management financial statements",
            "HOA board treasurer guide", "condo association budget",
            "property management accounting software",
        ],
        "publish_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "publish_time": "09:00",
        "post_length": 1600,
        "unsplash_fallback": "accounting finance office property management",
        "prompt_profile": {
            "brand": "Property Ledger Solutions",
            "audience": (
                "property management company owners, HOA and condo association board members/treasurers, "
                "and real estate investors in South Florida (and the wider US) who need reliable outsourced "
                "accounting instead of hiring and managing in-house accounting staff"
            ),
            "objective": (
                "capture organic traffic from property managers and HOA/condo boards searching for outsourced "
                "accounting, trust accounting compliance, and financial reporting help, and position Property "
                "Ledger Solutions as the specialized accounting partner that understands property management — "
                "not a generic bookkeeper"
            ),
            "tone": (
                "professional, precise and reassuring, in US English; explains accounting and compliance "
                "concepts in plain language for non-accountants (property managers, board members) while "
                "still sounding like a specialist firm"
            ),
            "angles": [
                "practical how-to guides for property managers (month-end close, reconciliations, owner statements)",
                "trust accounting compliance and best practices (state trust account rules, commingling risks)",
                "HOA/condo board financial reporting and audit-readiness",
                "signs it's time to outsource accounting / red flags with your current bookkeeping",
                "in-house bookkeeper vs outsourced accounting firm — how to decide",
                "software and tools property managers use for accounting (AppFolio, Buildium, QuickBooks)",
                "budgeting, reserves and variance analysis for HOAs and property managers",
            ],
            "categories": {
                "Trust Accounting": "trust account reconciliation, commingling risk, state trust account compliance",
                "Financial Reporting": "owner statements, financial statements, board reporting, audit-readiness",
                "Property Management Accounting": "general accounting operations, month-end close, AP/AR, bookkeeping",
                "HOA & Condo Accounting": "HOA and condo association specific content, reserves, budgets, treasurer guides",
            },
            "cta": (
                "close with a soft CTA inviting the reader to schedule a free consultation at "
                "propertyledger.us/contact or call (954) 261-1022"
            ),
            "internal_links": {
                "https://propertyledger.us/": "Property Ledger Solutions — home",
                "https://propertyledger.us/monthly-accounting/": "Monthly Accounting service",
                "https://propertyledger.us/property-management-accounting/": "Property Management Trust Accounting service",
                # NOTA: /hoa-condo-accounting/ está en BORRADOR (2026-07-20). Re-agregar
                # a internal_links cuando se republique, para que los blogs HOA la enlacen.
                "https://propertyledger.us/contact/": "Schedule a free consultation",
            },
        },
    },
}

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
