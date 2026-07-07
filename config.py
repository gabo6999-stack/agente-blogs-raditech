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
        },
    },
}

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
