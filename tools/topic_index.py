"""Indice de temas publicados por sitio (compuerta 3, anti-duplicados).

Guarda por cada post: titulo, H1, focus keyword de Rank Math y el conjunto de H2.
Se reconstruye desde WordPress (`refresh`) para no depender de un log local que se
borra en cada redeploy — que es justo lo que dejo publicar 9 temas por segunda y
tercera vez en propertyledger.us.
"""
import re
from difflib import SequenceMatcher

from tools import store
from tools.html_tools import analyze, normalize_text

STOPWORDS = set("""
a an the of for to in on and or with your you how what why is are be that this it
its as at from by not more when if we our us can do does guide best top vs than
el la los las un una de del y o con para por que como cual es son en su sus
""".split())


def normalize_title(text: str) -> str:
    """Minusculas, sin puntuacion, sin stopwords, y colapsando cadenas repetidas
    del tipo `X + X` — el patron que dejo el bug del H1 duplicado y que rompe
    cualquier comparacion literal."""
    t = normalize_text(text)
    t = re.sub(r"[^a-z0-9áéíóúñü\s]", " ", t)
    words = [w for w in t.split() if w not in STOPWORDS]

    # colapsa palabras repetidas consecutivas: "guide guide" -> "guide"
    dedup = []
    for w in words:
        if not dedup or dedup[-1] != w:
            dedup.append(w)

    # colapsa la cadena entera duplicada: "a b c a b c" -> "a b c"
    n = len(dedup)
    for size in range(n // 2, 1, -1):
        if n % size == 0 and len(set(tuple(dedup[i:i + size])
                                     for i in range(0, n, size))) == 1:
            dedup = dedup[:size]
            break
    return " ".join(dedup)


def _h2_set(h2_list) -> set:
    return {normalize_title(h) for h in (h2_list or []) if normalize_title(h)}


def load(site_key: str) -> dict:
    return store.load(site_key, "topic-index", {"posts": [], "refreshed_at": None})


def refresh(site_key: str) -> dict:
    """Reconstruye el indice leyendo WordPress. Incluye borradores y programados
    a proposito: un borrador ya ocupa el tema y su slug."""
    from datetime import datetime, timezone

    from tools.wordpress import fetch_posts_for_index
    posts = fetch_posts_for_index(site_key)
    idx = {"refreshed_at": datetime.now(timezone.utc).isoformat(), "posts": posts}
    store.save(site_key, "topic-index", idx)
    print(f"[topic-index] {site_key}: {len(posts)} posts indexados")
    return idx


def find_duplicates(site_key: str, title: str, h2_texts: list,
                    focus_keyword: str = "", slug: str = "",
                    h2_threshold: float = 0.60, title_threshold: float = 0.75,
                    exclude_id: int = None) -> list[dict]:
    """Devuelve los posts existentes que chocan con el articulo propuesto.

    Criterios (cualquiera dispara):
      - misma focus keyword de Rank Math
      - mismo slug
      - titulo normalizado con similitud >= title_threshold
      - solape del conjunto de H2 >= h2_threshold (Jaccard sobre H2 normalizados)
    """
    idx = load(site_key)
    if not idx.get("posts"):
        idx = refresh(site_key)

    nt = normalize_title(title)
    nh2 = _h2_set(h2_texts)
    fk = (focus_keyword or "").strip().lower()
    hits = []

    for p in idx.get("posts", []):
        if exclude_id and p.get("id") == exclude_id:
            continue
        motivos = []

        if fk and (p.get("focus_keyword") or "").strip().lower() == fk:
            motivos.append(f"misma focus keyword: {fk!r}")

        if slug and p.get("slug") == slug:
            motivos.append(f"mismo slug: {slug!r}")

        ratio = SequenceMatcher(None, nt, p.get("norm_title", "")).ratio() if nt else 0
        if ratio >= title_threshold:
            motivos.append(f"titulo {ratio:.0%} similar a #{p['id']}")

        # el H1 guardado tambien cuenta: los duplicados del 12-ago repetian el H1
        nh1 = normalize_title(p.get("h1") or "")
        if nh1 and nt and SequenceMatcher(None, nt, nh1).ratio() >= title_threshold:
            motivos.append(f"H1 existente {SequenceMatcher(None, nt, nh1).ratio():.0%} similar")

        other_h2 = set(p.get("norm_h2") or [])
        if nh2 and other_h2:
            inter = len(nh2 & other_h2)
            union = len(nh2 | other_h2)
            jac = inter / union if union else 0
            solape = inter / len(nh2) if nh2 else 0
            if solape >= h2_threshold:
                motivos.append(f"{solape:.0%} de los H2 ya existen en #{p['id']} (jaccard {jac:.0%})")

        if motivos:
            hits.append({"id": p.get("id"), "slug": p.get("slug"),
                         "title": p.get("title"), "status": p.get("status"),
                         "link": p.get("link"), "motivos": motivos,
                         "title_ratio": round(ratio, 3)})
    return hits


def record(site_key: str, post: dict, content: str, focus_keyword: str = ""):
    """Agrega (o actualiza) un post en el indice tras publicarlo."""
    idx = load(site_key)
    title = (post.get("title") or {}).get("rendered") or (post.get("title") or {}).get("raw", "")
    a = analyze(content or "")
    entry = {
        "id": post.get("id"),
        "slug": post.get("slug"),
        "title": normalize_text(title),
        "norm_title": normalize_title(title),
        "h1": "",
        "focus_keyword": focus_keyword,
        "h2": a["h2_texts"],
        "norm_h2": sorted(_h2_set(a["h2_texts"])),
        "status": post.get("status"),
        "link": post.get("link"),
        "date_gmt": post.get("date_gmt"),
    }
    idx["posts"] = [p for p in idx.get("posts", []) if p.get("id") != entry["id"]]
    idx["posts"].append(entry)
    store.save(site_key, "topic-index", idx)
    return entry


def used_focus_keywords(site_key: str) -> dict:
    idx = load(site_key)
    out = {}
    for p in idx.get("posts", []):
        fk = (p.get("focus_keyword") or "").strip().lower()
        if fk:
            out.setdefault(fk, []).append(p.get("id"))
    return out
