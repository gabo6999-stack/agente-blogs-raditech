"""Cruza la evidencia cruda: quien publico que, cuando, y con que defectos."""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")

STOP = set("""a an the of for to in on and or with your you how what why is are
be that this it its as at from by not more when if we our us can do does guide
best top vs than""".split())


def norm(text):
    t = re.sub(r"<[^>]+>", " ", text or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    words = [w for w in t.split() if w not in STOP]
    # colapsa "X X" repetido (patron del H1 duplicado)
    out = []
    for w in words:
        if not out or out[-1] != w:
            out.append(w)
    joined = " ".join(out)
    half = len(joined) // 2
    if half > 10 and joined[:half].strip() == joined[half:].strip():
        joined = joined[:half].strip()
    return joined


def main(site_key):
    with open(os.path.join(EV, f"{site_key}-posts.json"), encoding="utf-8") as f:
        data = json.load(f)
    posts = data["posts"]

    print("=" * 78)
    print("1. QUIEN PUBLICO QUE  (autor x defecto)")
    print("=" * 78)
    by_author = defaultdict(list)
    for p in posts:
        by_author[p["author"]].append(p)
    for author, ps in sorted(by_author.items()):
        print(f"\n-- {author}: {len(ps)} posts  ({min(p['date_gmt'] for p in ps)} .. {max(p['date_gmt'] for p in ps)})")
        print(f"   sin rank_math_seo_score : {sum(1 for p in ps if not p['rank_math_seo_score'])}/{len(ps)}")
        print(f"   sin rank_math_title     : {sum(1 for p in ps if not p['rank_math_title'])}/{len(ps)}")
        print(f"   Uncategorized           : {sum(1 for p in ps if p['categories'] == ['Uncategorized'])}/{len(ps)}")
        print(f"   con <h1> en el cuerpo   : {sum(1 for p in ps if p['h1_in_body'])}/{len(ps)}")
        print(f"   slug con sufijo -N      : {sum(1 for p in ps if re.search(r'-[0-9]+$', p['slug'] or ''))}/{len(ps)}")
        scores = [p["rank_math_seo_score"] for p in ps if p["rank_math_seo_score"]]
        print(f"   seo_score presentes     : {sorted(scores)}")

    print()
    print("=" * 78)
    print("2. LINEA DE TIEMPO (UTC)")
    print("=" * 78)
    print(f"{'fecha_gmt':<21}{'aut':<10}{'est':<8}{'score':<6}{'cat':<28}{'h1':<4}slug")
    for p in sorted(posts, key=lambda x: x["date_gmt"] or ""):
        cat = ",".join(p["categories"])[:26]
        print(f"{(p['date_gmt'] or '')[:19]:<21}{p['author'][:9]:<10}{p['status'][:7]:<8}"
              f"{str(p['rank_math_seo_score'] or '-'):<6}{cat:<28}{p['h1_in_body']:<4}{p['slug'][:44]}")

    print()
    print("=" * 78)
    print("3. RAFAGAS: publicaciones por dia y separacion minima")
    print("=" * 78)
    per_day = Counter((p["date_gmt"] or "")[:10] for p in posts)
    for day, n in sorted(per_day.items()):
        flag = "  <-- RAFAGA" if n > 2 else ""
        print(f"  {day}: {n}{flag}")
    ordered = sorted([p for p in posts if p["date_gmt"]], key=lambda x: x["date_gmt"])
    from datetime import datetime
    print("\n  gaps < 4h entre publicaciones consecutivas:")
    found = False
    for a, b in zip(ordered, ordered[1:]):
        ta = datetime.fromisoformat(a["date_gmt"])
        tb = datetime.fromisoformat(b["date_gmt"])
        gap = (tb - ta).total_seconds() / 3600
        if gap < 4:
            found = True
            print(f"    {gap:5.2f}h  {a['slug'][:38]:<40} -> {b['slug'][:38]}  [{a['author']}/{b['author']}]")
    if not found:
        print("    (ninguno)")

    print()
    print("=" * 78)
    print("4. DUPLICADOS DE TEMA (titulo normalizado, similitud >= 0.60)")
    print("=" * 78)
    normed = [(p, norm(p["title"])) for p in posts]
    seen = set()
    dupes = 0
    for i, (pa, na) in enumerate(normed):
        group = [pa]
        for pb, nb in normed[i + 1:]:
            if pb["id"] in seen:
                continue
            if SequenceMatcher(None, na, nb).ratio() >= 0.60:
                group.append(pb)
        if len(group) > 1 and pa["id"] not in seen:
            dupes += 1
            for g in group:
                seen.add(g["id"])
            print(f"\n  GRUPO {dupes}:")
            for g in group:
                print(f"    #{g['id']:<5} {g['status']:<8} {(g['date_gmt'] or '')[:10]}  /{g['slug']}")
                print(f"           titulo: {g['title'][:90]}")
    if not dupes:
        print("  (ninguno)")

    print()
    print("=" * 78)
    print("5. FOCUS KEYWORDS REPETIDAS")
    print("=" * 78)
    fk = Counter((p["rank_math_focus_keyword"] or "").strip().lower() for p in posts)
    for k, n in fk.most_common():
        if n > 1 and k:
            ids = [p["id"] for p in posts if (p["rank_math_focus_keyword"] or "").strip().lower() == k]
            print(f"  x{n}  '{k}'  -> posts {ids}")

    print()
    print("=" * 78)
    print("6. H1 EN EL CUERPO — texto vs titulo del post")
    print("=" * 78)
    for p in posts:
        if p["h1_in_body"]:
            same = any(norm(h) == norm(p["title"]) for h in p["h1_texts"])
            print(f"  #{p['id']} [{p['author']}] h1x{p['h1_in_body']} igual_al_titulo={same}")
            print(f"      titulo : {p['title'][:88]}")
            for h in p["h1_texts"]:
                print(f"      h1     : {h[:88]}")

    print()
    print("=" * 78)
    print("7. LONGITUD DEL CUERPO (solo el content del post, no la plantilla)")
    print("=" * 78)
    ws = sorted(p["word_count_body"] for p in posts)
    print(f"  min={ws[0]}  mediana={ws[len(ws)//2]}  max={ws[-1]}")
    cortos = [p for p in posts if p["word_count_body"] < 900]
    print(f"  bajo 900 palabras: {len(cortos)} -> {[(p['id'], p['word_count_body']) for p in cortos]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "propertyledger")
