import json
import os
import random
from pytrends.request import TrendReq
from config import SITES

# Cola de temas curada (DataForSEO). Si existe content_cache/<site_key>.json con
# un "blog_queue", el agente publica de ahí en orden (temas medidos por volumen/KD)
# en vez de tendencias. Cuando se agota, cae de nuevo a Google Trends.
_QUEUE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content_cache")


def get_queued_topic(site_key: str, used_topics: list[str]) -> str | None:
    """Siguiente tema de la cola curada que no se haya publicado. None si no hay
    cola o ya se agotó."""
    path = os.path.join(_QUEUE_DIR, f"{site_key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception as e:
        print(f"[Queue] No se pudo leer {path}: {e}")
        return None
    used = set(used_topics)
    for entry in sorted(cache.get("blog_queue", []), key=lambda e: e.get("order", 0)):
        topic = entry.get("topic")
        if topic and topic not in used:
            print(f"[Queue] {site_key}: tema #{entry.get('order')} de la cola -> {topic}")
            return topic
    print(f"[Queue] {site_key}: cola agotada, usando tendencias")
    return None


def get_trending_topics(site_key: str) -> list[str]:
    """
    Obtiene tendencias relevantes para el nicho del sitio.
    Combina Google Trends con keywords seed del config.
    """
    site = SITES[site_key]
    keywords_seed = site["keywords_seed"]
    language = site.get("language", "es")
    hl, geo = ('en-US', 'US') if language == 'en' else ('es-MX', 'MX')

    try:
        pytrends = TrendReq(hl=hl, tz=360)

        # Buscar tendencias relacionadas con keywords seed (en grupos de 5)
        trending = []
        sample_keywords = random.sample(keywords_seed, min(5, len(keywords_seed)))

        pytrends.build_payload(sample_keywords, cat=0, timeframe='now 7-d', geo=geo)
        related = pytrends.related_queries()

        for kw in sample_keywords:
            if related.get(kw) and related[kw].get('top') is not None:
                top_queries = related[kw]['top']['query'].tolist()[:3]
                trending.extend(top_queries)

        # Si no hay tendencias, usar keywords seed directamente
        if not trending:
            trending = keywords_seed

        # Mezclar y retornar top 10 únicos
        unique_trending = list(dict.fromkeys(trending))
        random.shuffle(unique_trending)
        return unique_trending[:10]

    except Exception as e:
        print(f"[Trends] Error obteniendo tendencias: {e}")
        # Fallback a keywords seed
        shuffled = keywords_seed.copy()
        random.shuffle(shuffled)
        return shuffled[:10]


def pick_topic(site_key: str, used_topics: list[str] = []) -> str:
    """
    Selecciona el tema más relevante que no haya sido usado recientemente.
    Prioridad: cola curada (DataForSEO) -> Google Trends -> keyword seed.
    """
    queued = get_queued_topic(site_key, used_topics)
    if queued:
        return queued

    topics = get_trending_topics(site_key)
    
    for topic in topics:
        if topic not in used_topics:
            return topic
    
    # Si todos fueron usados, regresar el primero de todos modos
    return topics[0] if topics else SITES[site_key]["keywords_seed"][0]
