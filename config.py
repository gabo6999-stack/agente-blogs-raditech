import os
from dotenv import load_dotenv

load_dotenv()

SITES = {
    "raditech": {
        "wp_url": os.getenv("SITE1_WP_URL"),
        "wp_user": os.getenv("SITE1_WP_USER"),
        "wp_password": os.getenv("SITE1_WP_PASSWORD"),
        # G01 abre el editor con wp-login.php, que no acepta una contraseña de aplicación.
        # Si SITE1_WP_PASSWORD lo es, definir aquí la contraseña real de la cuenta.
        "wp_login_password": os.getenv("SITE1_WP_LOGIN_PASSWORD"),
        # Sin schema FAQPage: dentro del content lo rechaza G07e, y guardado en Rank Math
        # (faq_schema_via_meta) desplaza al BlogPosting y al autor — medido en cmlc el
        # 24-oct-2026. Google ya no muestra el rich result de FAQ en este tipo de sitio.
        # La FAQ visible se queda.
        "sin_faq_schema": True,
        "category": "Tecnología médica",
        "niche": "software médico, sistemas PACS-RIS, teleradiología e imagen médica digital en México",
        "language": "es",
        "keywords_seed": [
            "PACS México", "sistema PACS hospital", "teleradiología",
            "RIS radiología", "imágenes médicas digitales",
            "DICOM viewer", "radiología digital", "software médico hospital",
            "gestión de estudios radiológicos", "VIRA PACS", "teleradiología 24/7",
            # Sin HIS ni expediente clínico: Raditech dejó de vender HIS el 6-ago-2026.
            "radiología a distancia", "interoperabilidad HL7 FHIR",
            "inteligencia artificial radiología", "workstation radiología",
            "monitor médico diagnóstico", "seguridad informática salud",
        ],
        "publish_days": ["monday", "tuesday", "thursday", "friday"],
        "publish_time": "09:00",
        "post_length": 1800,
        "unsplash_fallback": "hospital radiology technology medical imaging",
        # Hasta el 24-oct-2026 raditech usaba _get_raditech_prompt, sin páginas internas
        # ni enlaces externos: G09 lo rechazaba siempre. El perfil conserva su tono y
        # sus ángulos y le da las páginas reales (todas verificadas en 200, sin redirección).
        "prompt_profile": {
            "brand": "Raditech",
            "audience": (
                "tomadores de decisión del sector salud en México y Latinoamérica: directores "
                "médicos, jefes de radiología, gerentes de TI hospitalario y administradores de "
                "clínicas y hospitales que evalúan, comparan o implementan PACS, RIS o teleradiología"
            ),
            "objective": (
                "capturar tráfico orgánico B2B de decisores que están evaluando soluciones de "
                "imagenología digital, PACS, RIS o teleradiología, y posicionar a Raditech (VIRA PACS, "
                "PACS-RIS, teleradiología 24/7) como referencia técnica que genera confianza institucional"
            ),
            "tone": (
                "técnico-profesional e institucional, orientado a ROI y eficiencia operativa, en español "
                "de México, con los términos en inglés que son estándar del sector (PACS, DICOM, RIS, HL7, "
                "FHIR); sin lenguaje de ventas directo: el valor surge del expertise demostrado, con datos, "
                "estándares (DICOM, HL7, IHE) y escenarios reconocibles para hospitales y clínicas"
            ),
            "angles": [
                "ROI y reducción de costos operativos (menos papel, menos tiempo, menos errores)",
                # Sin HIS, expediente clínico ni NOM-004: Raditech dejó de vender HIS el 6-ago-2026.
                "cumplimiento normativo en México (NOM-024, protección de datos en salud)",
                "interoperabilidad: DICOM y HL7 FHIR para que el PACS se integre con los sistemas del hospital",
                "flujo de trabajo clínico: menos tiempo de espera y reportes más rápidos",
                "teleradiología como respuesta a la escasez de radiólogos en regiones remotas",
                "seguridad de datos en imagenología (cifrado, acceso controlado, trazabilidad)",
                "IA aplicada a radiología (detección asistida, priorización de estudios urgentes)",
                "criterios para evaluar y comparar sistemas PACS en un hospital",
            ],
            "categories": {
                "Diagnóstico por imagen": "PACS, DICOM, RIS, workstations, monitores médicos y modalidades de imagen (TAC, RM, rayos X)",
                "Teleradiología": "teleradiología, interpretación remota, radiólogos y subespecialistas a distancia",
                "Gestión hospitalaria": "digitalización del servicio de imagen, flujo de trabajo y eficiencia operativa del área de radiología",
                "Tecnología médica": "IA en radiología, interoperabilidad HL7/FHIR, ciberseguridad en salud, tendencias del sector",
            },
            "cta": (
                "cierre institucional sutil invitando a conocer la solución pertinente de Raditech "
                "(VIRA PACS, PACS-RIS o el servicio de teleradiología) enlazando su página de producto, "
                "o a solicitar una demostración en https://raditech.mx/contacto/ — nunca lenguaje de venta agresivo"
            ),
            "title_rules": (
                "- El título nombra el tema CONCRETO del artículo y lo que el lector se lleva (un criterio, una comparación, "
                "un costo, unos pasos, un cambio de norma), no una fórmula genérica.\n"
                "- PROHIBIDO usar las fórmulas que ya se repiten en el blog: «Guía Completa», «Guía Definitiva», "
                "«para Hospitales y Clínicas en México», «Todo lo que necesitas saber». Varios posts ya se titulan así y "
                "el filtro de duplicados rechaza cualquier título parecido a ellos aunque el tema sea otro.\n"
                "- México o el año, como mucho una vez y solo si aportan.\n"
                "- Estilo buscado: «Monitor médico diagnóstico: 7 criterios para elegirlo según la modalidad», "
                "«PACS en la nube o local: qué cambia en costo, seguridad y soporte», "
                "«BI-RADS v2025: qué cambia para los servicios de radiología e imagen mamaria»."
            ),
            "external_examples": (
                "el estándar DICOM (dicomstandard.org), HL7 (hl7.org), las normas oficiales mexicanas en "
                "el DOF, la Secretaría de Salud, la OMS, RSNA, ACR o estudios indexados en PubMed"
            ),
            "internal_links": {
                "https://raditech.mx/sistema-pacs-ris/": "PACS-RIS para áreas de radiología",
                "https://raditech.mx/pacs-teleradiologia/": "VIRA PACS con teleradiología integrada",
                "https://raditech.mx/servicio-teleradiologia/": "Servicio de teleradiología 24/7 para hospitales",
                "https://raditech.mx/teleradiologia-alta-especialidad/": "Teleradiología de alta especialidad con subespecialistas",
                "https://raditech.mx/teleradiologia-resonancia-cardiovascular/": "Interpretación remota de resonancia magnética cardiovascular (CMR)",
                "https://raditech.mx/teleradiologia-tomografia-cardiaca/": "Interpretación remota de tomografía cardiaca y angio-TAC coronaria",
                "https://raditech.mx/monitores-medicos-radiologia/": "Monitores médicos de grado diagnóstico DICOM",
                "https://raditech.mx/portal-x-card/": "Portal X-Card: entrega digital de estudios al paciente",
                "https://raditech.mx/nuestros-productos/": "Todas las soluciones de Raditech",
                "https://raditech.mx/contacto/": "Solicitar una demostración o cotización",
                "https://raditech.mx/sistema-pacs-hospital-guia-completa-digitalizacion/": "Guía: qué es un PACS y cómo funciona en un hospital",
                "https://raditech.mx/ris-radiologia-sistema-informacion-radiologica/": "Guía: qué es un sistema RIS",
                "https://raditech.mx/dicom-viewer-guia-completa-hospitales-clinicas-mexico/": "Guía: qué es DICOM y para qué sirve un visor",
                "https://raditech.mx/teleradiologia-solucion-estrategica-hospitales-clinicas-mexico/": "Guía: la teleradiología como solución para hospitales y clínicas",
                "https://raditech.mx/inteligencia-artificial-radiologia-diagnostica-mexico-2026/": "Guía: inteligencia artificial en radiología diagnóstica",
                "https://raditech.mx/publicamos-un-glosario-abierto-de-pacs-ris-dicom-y-hl7/": "Glosario abierto de PACS, RIS, DICOM y HL7",
            },
            # G09c: al menos un enlace a una de estas. Las guías no cuentan como servicio.
            "service_pages": [
                "https://raditech.mx/sistema-pacs-ris/",
                "https://raditech.mx/pacs-teleradiologia/",
                "https://raditech.mx/servicio-teleradiologia/",
                "https://raditech.mx/teleradiologia-alta-especialidad/",
                "https://raditech.mx/teleradiologia-resonancia-cardiovascular/",
                "https://raditech.mx/teleradiologia-tomografia-cardiaca/",
                "https://raditech.mx/monitores-medicos-radiologia/",
                "https://raditech.mx/portal-x-card/",
                "https://raditech.mx/nuestros-productos/",
                "https://raditech.mx/contacto/",
            ],
        },
    },
    "tnrvisual": {
        "wp_url": os.getenv("SITE2_WP_URL"),
        "wp_user": os.getenv("SITE2_WP_USER"),
        "wp_password": os.getenv("SITE2_WP_PASSWORD"),
        "sin_faq_schema": True,  # mismo motivo que raditech (G07e vs <script> FAQ)
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
        # wp_password es un Application Password (para REST); wp-login.php no lo acepta.
        # G01 (score real de Rank Math vía navegador) necesita la contraseña real de la
        # cuenta, por eso existe esta clave aparte. Ver tools.rankmath_browser._parece_app_password.
        "wp_login_password": os.getenv("SITE3_WP_LOGIN_PASSWORD"),
        "category": "Radiología e Imagen",
        # Categoría de servicio determinista para las migas de pan: se evalúa EN ORDEN y
        # gana la primera coincidencia (por eso 'panorámica dental' no cae en Rayos X).
        # Palabras clave en minúsculas y sin acentos; sin coincidencia -> "category".
        # Ver tools.categories.pick_category.
        "category_rules": [
            ("Mastografía", ["mastograf", "mamograf", "bi-rads", "birads", "mama"]),
            ("Panorámica dental", ["panoramic", "ortopantomograf", "dental"]),
            ("Tomografía", ["tomograf", "tac", "escaner"]),
            ("Ultrasonido", ["ultrasonid", "ecograf", "sonograf"]),
            ("Rayos X", ["rayos x", "radiograf", "placa de torax"]),
            ("Otros estudios", ["densitometr", "electrocardiograf", "resonancia"]),
        ],
        "niche": "radiología e imagenología diagnóstica para pacientes (rayos X, tomografía, ultrasonido, mastografía) en Mazatlán, Sinaloa",
        "language": "es",
        # La cuenta publicadora (pedrogavito) es 'author': WordPress borra el
        # <script> ld+json del content al guardar. Se persiste el FAQPage schema
        # vía Rank Math meta (rankmath/v1/updateMeta), que sí sobrevive. Ver
        # tools.wordpress.set_faq_schema_meta.
        "faq_schema_via_meta": True,
        "keywords_seed": [
            "historia de la radiología", "rayos x Mazatlán", "tomografía Mazatlán",
            "estudios de imagen Mazatlán", "ultrasonido Mazatlán", "mastografía Mazatlán",
            "rayos x a domicilio", "preparación para tomografía", "qué es una densitometría ósea",
            "radiología e imagen", "panorámica dental Mazatlán", "electrocardiograma Mazatlán",
            "resonancia magnética Mazatlán", "densitometría ósea Mazatlán", "rayos x de columna Mazatlán",
            "ultrasonido obstétrico Mazatlán", "BI-RADS mastografía resultados", "preparación para estudios de imagen",
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
        # Compuerta 1 (puntuación real de Rank Math). La contraseña de aplicación
        # sirve para la REST API pero NO para wp-login.php, y el editor de bloques
        # sólo se abre con sesión de wp-admin. Sin esta variable, la compuerta 1
        # falla y el post se queda en borrador — que es el comportamiento correcto,
        # pero significa que el agente no publicará nada hasta configurarla.
        "wp_login_password": os.getenv("SITE4_WP_LOGIN_PASSWORD"),
        "sin_faq_schema": True,  # mismo motivo que raditech: G07e lo rechazó a diario (visto del 19 al 23-oct)
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
            # Solo categorías que EXISTEN de verdad en el sitio. Comprobado el
            # 14-ago-2026 vía GET /wp/v2/categories: el sitio tiene exactamente
            # 'Trust Accounting' (26), 'Property Management Accounting' (11),
            # 'HOA &amp; Condo Accounting' (22) y 'Uncategorized' (1).
            # 'Financial Reporting' NO existe: estaba aquí y no en WordPress. La
            # compuerta 6 prohíbe crear categorías nuevas sin aprobación, así que
            # ofrecerla aquí solo consigue que el post caiga en Uncategorized.
            "categories": {
                "Trust Accounting": "trust account reconciliation, commingling risk, state trust account compliance",
                "Property Management Accounting": "general accounting operations, month-end close, AP/AR, bookkeeping, owner statements, financial statements, board reporting",
                "HOA & Condo Accounting": "HOA and condo association specific content, reserves, budgets, treasurer guides",
            },
            "cta": (
                "close with a soft CTA inviting the reader to schedule a free consultation at "
                "propertyledger.us/contact or call (954) 261-1022"
            ),
            # Verificado el 14-ago-2026 con peticiones SIN seguir redirecciones y
            # User-Agent Googlebot (3 intentos por URL, resultado estable 3/3).
            # Se quitaron dos entradas que estaban rotas y que el redactor venía
            # inyectando en los artículos (el post #322 enlazaba la primera dos veces):
            #   /hoa-condo-accounting/                                  -> 404 (Chrome y Googlebot)
            #   /hoa-accounting-basics-guide-board-members-treasurers/  -> 404 para Googlebot;
            #       es el post #115, que sigue en BORRADOR. Volver a ponerlo aquí solo
            #       cuando esté publicado y devuelva 200.
            # De todas formas la compuerta 9 revalida cada enlace en cada artículo:
            # esta lista es la fuente del redactor, no la última palabra.
            "internal_links": {
                # Páginas de servicio
                "https://propertyledger.us/": "Property Ledger Solutions — home",
                "https://propertyledger.us/monthly-accounting/": "Monthly Accounting service",
                "https://propertyledger.us/property-management-accounting/": "Property Management Trust Accounting service",
                "https://propertyledger.us/contact/": "Schedule a free consultation",
                # Blogs pilar (para cross-linking del cluster)
                "https://propertyledger.us/what-is-trust-accounting-property-management-guide/": "What is trust accounting in property management (guide)",
                "https://propertyledger.us/property-management-trust-accounting/": "Property management trust accounting: reconciliation guide",
                "https://propertyledger.us/property-management-financial-statements/": "Property management financial statements explained",
            },
        },
    },
}

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
