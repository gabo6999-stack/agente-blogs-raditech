import os
from dotenv import load_dotenv

load_dotenv()

SITES = {
    "raditech": {
        "wp_url": os.getenv("SITE1_WP_URL"),
        "wp_user": os.getenv("SITE1_WP_USER"),
        "wp_password": os.getenv("SITE1_WP_PASSWORD"),
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
    }
}

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
