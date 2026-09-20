#!/usr/bin/env python3
"""Build animalstats.org into output/.

    python3 build.py            # build (compiles Tailwind first when node_modules is present)
    python3 build.py --no-css   # use the committed static/css/site.css (what CI does)
"""

import json
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")
DATA = os.path.join(ROOT, "data")
CSS = os.path.join(ROOT, "static", "css", "site.css")

POPULAR = ["cat", "dog", "lion", "tiger", "african-elephant", "blue-whale", "great-white-shark", "cheetah", "giraffe",
           "gray-wolf", "bald-eagle", "polar-bear", "gorilla", "horse", "orca", "honey-bee", "king-cobra",
           "green-sea-turtle", "axolotl", "peregrine-falcon", "galapagos-tortoise", "monarch-butterfly", "rabbit", "koala"]

TO_YEARS = {"years": 1, "months": 1 / 12, "weeks": 1 / 52.18, "days": 1 / 365.25, "hours": 1 / 8766}
TO_KG = {"kg": 1, "g": 1e-3, "mg": 1e-6}
TO_M = {"m": 1, "cm": 1e-2, "mm": 1e-3}
IUCN_RANK = {"EX": 7, "EW": 6, "CR": 5, "EN": 4, "VU": 3, "NT": 2, "LC": 1, "DD": 0, "NE": 0, "DOM": 0}
TREND_RANK = {"Decreasing": 2, "Unknown": 1, "Stable": 0, "Increasing": -1}


def read(name):
    return json.load(open(os.path.join(DATA, name), encoding="utf-8"))


def load_animals():
    out = {}
    adir = os.path.join(DATA, "animals")
    for name in sorted(os.listdir(adir)):
        if name.endswith(".json"):
            d = json.load(open(os.path.join(adir, name), encoding="utf-8"))
            out[d["slug"]] = d
    return out


def aliases():
    out = {}
    for line in open(os.path.join(DATA, "master_list.txt"), encoding="utf-8"):
        if "|" in line and not line.startswith("#"):
            p = [x.strip() for x in line.split("|")]
            out[p[0]] = [a.strip() for a in p[3].split(",") if a.strip()] if len(p) > 3 else []
    return out


def icon_factory():
    cache = {}

    def icon(name, cls="w-5 h-5"):
        if name not in cache:
            raw = open(os.path.join(ROOT, "icons", name + ".svg"), encoding="utf-8").read()
            inner = raw[raw.index(">", raw.index("<svg")) + 1:raw.rindex("</svg>")]
            cache[name] = re.sub(r"\s+", " ", inner).strip()
        return Markup(f'<svg class="{cls}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
                      f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                      f'aria-hidden="true">{cache[name]}</svg>')
    return icon


def jsonld(obj):
    return Markup('<script type="application/ld+json">'
                  + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>")


def compile_css():
    binary = os.path.join(ROOT, "node_modules", ".bin", "tailwindcss")
    if "--no-css" in sys.argv or not os.path.exists(binary):
        print("css: using committed static/css/site.css")
        return
    subprocess.run([binary, "-c", "tailwind.config.js", "-i", "src/input.css", "-o", CSS, "--minify"],
                   cwd=ROOT, check=True, capture_output=True)
    print(f"css: compiled {os.path.getsize(CSS) / 1024:.1f} KB")


def cap(s):
    return s[:1].upper() + s[1:]


def enrich(a):
    """Add normalised numbers (for sorting) and heading strings to an animal record."""
    f = a["facts"]
    n = {}
    life, capt = f.get("lifespan"), f.get("lifespanCaptivity")
    n["lifespan"] = life["max"] * TO_YEARS[life["unit"]] if life else None
    n["longevity"] = max([x["max"] * TO_YEARS[x["unit"]] for x in (life, capt) if x] or [0]) or None
    n["weight"] = f["weight"]["max"] * TO_KG[f["weight"]["unit"]] if f.get("weight") else None
    n["height"] = f["height"]["max"] * TO_M[f["height"]["unit"]] if f.get("height") else None
    n["speed"] = f["speed"]["max"] if f.get("speed") else None
    n["gestation"] = f["gestationPeriod"]["max"] if f.get("gestationPeriod") else None
    a["n"] = n
    a["url"] = f"/animals/{a['slug']}/"
    sing, plur, art = a["nameSingular"], a["namePlural"], a["article"]
    size_label = f["height"]["label"] if f.get("height") else "Height"
    size_q = {"Height": f"How Tall Is {art} {sing}?", "Shoulder height": f"How Tall Is {art} {sing}?",
              "Wingspan": f"How Big Is {art} {sing}?"}.get(size_label, f"How Long Is {art} {sing}?")
    verb = (f.get("speed") or {}).get("verb", "move")
    glabel = (f.get("gestationPeriod") or {}).get("label")
    gest_q = {"Gestation": f"How Long Is {art} {sing} Pregnant?",
              "Incubation": f"How Long Do {plur} Eggs Take to Hatch?",
              "Egg development": f"How Long Do {plur} Eggs Take to Hatch?"}.get(glabel)
    a["headings"] = OrderedDict([
        ("lifespan", f"How Long Do {plur} Live?"),
        ("weight", f"How Much Does {art} {sing} Weigh?"),
        ("size", size_q),
        ("speed", f"How Fast Can {art} {sing} {cap(verb)}?" if f.get("speed") else None),
        ("gestation", gest_q if f.get("gestationPeriod") else None),
        ("diet", f"What Do {plur} Eat?"),
        ("habitat", f"Where Do {plur} Live?"),
        ("conservation", f"Are {plur} Endangered?"),
    ])
    a["headings"] = OrderedDict((k, title_case(v)) for k, v in a["headings"].items() if v and a["answers"].get(k))
    return a


def title_case(s):
    """Capitalise the first letter of each word in a heading without touching the rest (keeps 'African', 'pH')."""
    small = {"a", "an", "the", "to", "of", "in", "and", "or", "vs"}
    words = s.split(" ")
    return " ".join(w if (i and w.lower() in small) else cap(w) for i, w in enumerate(words))


def build_lists(defs, animals, classes):
    out = []
    for d in defs:
        flt = d.get("filter", {})
        rows = []
        for a in animals.values():
            f = a["facts"]
            if flt.get("class") and a["taxonomy"]["classSlug"] != flt["class"]:
                continue
            if flt.get("verb") and (f.get("speed") or {}).get("verb") != flt["verb"]:
                continue
            if d["metric"] == "endangered":
                cat = a["ecology"]["iucnCategory"]
                if cat not in ("CR", "EN", "VU"):
                    continue
                rows.append((IUCN_RANK[cat] * 10 + TREND_RANK.get(a["ecology"]["populationTrend"], 0), a,
                             a["ecology"]["conservationStatus"],
                             a["ecology"].get("population") or f"Population {a['ecology']['populationTrend'].lower()}"))
                continue
            key = {"speed": "speed", "gestation": "gestationPeriod", "height": "height", "weight": "weight",
                   "lifespan": "lifespan", "longevity": "lifespan"}[d["metric"]]
            fact = f.get(key)
            if not fact:
                continue
            if flt.get("labels") and fact.get("label") not in flt["labels"]:
                continue
            value, display, note = a["n"][d["metric"]], fact["display"], fact.get("context") or fact.get("label") or ""
            if d["metric"] == "longevity":
                capt = f.get("lifespanCaptivity")
                if capt and capt["max"] * TO_YEARS[capt["unit"]] > a["n"]["lifespan"]:
                    display, note = capt["display"], capt.get("context", "in human care")
            if d["metric"] == "height":
                note = fact["label"].lower()
            if value is None:
                continue
            rows.append((value, a, display, note))
        rows.sort(key=lambda r: (-r[0] if d["order"] == "desc" else r[0], r[1]["commonName"]))
        rows = rows[:25]
        if len(rows) < 5:
            continue
        item = dict(d, url=f"/lists/{d['slug']}/", rows=[{"rank": i + 1, "animal": r[1], "display": r[2], "note": r[3]}
                                                        for i, r in enumerate(rows)])
        out.append(item)
        for r in item["rows"]:
            r["animal"]["appearsInLists"].append({"title": d["title"], "url": item["url"], "rank": r["rank"]})
    return out


def main():
    site, classes, animals = read("site.json"), read("classes.json"), load_animals()
    compile_css()
    css = open(CSS, encoding="utf-8").read()
    alias = aliases()
    class_by_slug = {c["slug"]: c for c in classes}
    for a in animals.values():
        a["appearsInLists"] = []
        a["cls"] = class_by_slug[a["taxonomy"]["classSlug"]]
        a["aliases"] = alias.get(a["slug"], [])
        enrich(a)
    for a in animals.values():
        a["related"] = [animals[s] for s in a["relatedAnimals"] if s in animals]
    for c in classes:
        c["url"] = f"/{c['slug']}/"
        c["animals"] = sorted((a for a in animals.values() if a["taxonomy"]["classSlug"] == c["slug"]),
                              key=lambda a: a["commonName"])
        groups = OrderedDict()
        for a in sorted(c["animals"], key=lambda a: (a["taxonomy"]["order"], a["commonName"])):
            groups.setdefault(a["taxonomy"]["order"], []).append(a)
        c["groups"] = list(groups.items())
    classes = [c for c in classes if c["animals"]]

    lists = build_lists(read("lists.json"), animals, classes)
    list_by_slug = {l["slug"]: l for l in lists}
    facts = [dict(f, url=f"/facts/{f['slug']}/", toplist=list_by_slug.get(f.get("list"))) for f in read("facts.json")]

    comparisons = []
    for c in read("comparisons.json"):
        path = os.path.join(DATA, "comparisons", c["slug"] + ".json")
        if c["a"] in animals and c["b"] in animals and os.path.exists(path):
            text = json.load(open(path, encoding="utf-8"))
            comparisons.append(dict(c, text=text, A=animals[c["a"]], B=animals[c["b"]], url=f"/compare/{c['slug']}/"))
    for c in comparisons:
        for k in ("A", "B"):
            c[k].setdefault("comparisons", []).append(c)

    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")),
                      autoescape=select_autoescape(["html", "xml"]), trim_blocks=True, lstrip_blocks=True)
    env.globals.update(site=site, classes=classes, icon=icon_factory(), jsonld=jsonld, css=Markup(css),
                       year=site["updated"][:4], animal_count=len(animals), lists=lists, facts=facts,
                       comparisons=comparisons)

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(ROOT, "static"), OUT, ignore=shutil.ignore_patterns("css"))

    urls = {"animals": [], "compare": [], "lists": [], "pages": []}

    def render(template, path, group="pages", priority=0.5, filename="index.html", **ctx):
        html = env.get_template(template).render(path=path, canonical=site["url"] + path, **ctx)
        dest = os.path.join(OUT, path.strip("/"), filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(html)
        if filename == "index.html" and not ctx.get("noindex"):
            urls[group].append((path, priority))

    def crumbs_schema(crumbs):
        return {"@context": "https://schema.org", "@type": "BreadcrumbList",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": site["url"] + p}
                                    for i, (n, p) in enumerate(crumbs)]}

    def faq_schema(items):
        return {"@context": "https://schema.org", "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": q["question"],
                                "acceptedAnswer": {"@type": "Answer", "text": q["answer"]}} for q in items]}

    def itemlist(name, items):
        return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "numberOfItems": len(items),
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": x["commonName"],
                                     "url": site["url"] + x["url"]} for i, x in enumerate(items)]}

    org = {"@type": "Organization", "name": site["name"], "url": site["url"] + "/",
           "logo": {"@type": "ImageObject", "url": site["url"] + "/icon-512.png"}}

    def article(title, desc, path):
        return {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
                "mainEntityOfPage": site["url"] + path, "dateModified": site["updated"],
                "datePublished": site["updated"], "inLanguage": "en", "image": site["url"] + "/og-default.png",
                "author": org, "publisher": org}

    # ---- animal pages
    for a in animals.values():
        crumbs = [("Home", "/"), (a["cls"]["name"], a["cls"]["url"]), (a["commonName"], a["url"])]
        # The heading questions are part of the FAQ schema too: they are the queries the page answers.
        faq_items = [{"question": h, "answer": a["answers"][k]} for k, h in a["headings"].items()] + a["faq"]
        render("animal.html", a["url"], "animals", 0.8, animal=a, crumbs=crumbs,
               schema=[crumbs_schema(crumbs), faq_schema(faq_items),
                       article(a["meta"]["title"], a["meta"]["description"], a["url"])],
               title=a["meta"]["title"], description=a["meta"]["description"])

    # ---- class pages
    for c in classes:
        crumbs = [("Home", "/"), (c["name"], c["url"])]
        ex = c["animals"][:3]
        desc = (f"Facts for {len(c['animals'])} {c['name'].lower()}: lifespan, weight, size, speed and conservation status. "
                f"Includes {', '.join(x['commonName'].lower() for x in ex)} and more.")
        render("class.html", c["url"], "pages", 0.7, cls=c, crumbs=crumbs,
               schema=[crumbs_schema(crumbs), itemlist(c["name"], c["animals"])],
               title=f"{c['name']}: Facts, Lifespan, Size & Speed Chart", description=desc[:158])

    # ---- comparisons
    for c in comparisons:
        crumbs = [("Home", "/"), ("Compare", "/compare/"), (c["title"], c["url"])]
        render("compare.html", c["url"], "compare", 0.7, cmp=c, crumbs=crumbs,
               schema=[crumbs_schema(crumbs), faq_schema(c["text"]["faq"]),
                       article(c["text"]["meta"]["title"], c["text"]["meta"]["description"], c["url"])],
               title=c["text"]["meta"]["title"], description=c["text"]["meta"]["description"])
    crumbs = [("Home", "/"), ("Compare", "/compare/")]
    render("compare_index.html", "/compare/", "compare", 0.6, crumbs=crumbs, schema=[crumbs_schema(crumbs)],
           title="Animal Comparisons: Side-by-Side Differences",
           description=f"{len(comparisons)} side-by-side animal comparisons with size, speed and lifespan data: lion vs tiger, alligator vs crocodile, frog vs toad and more.")

    # ---- leaderboards
    for l in lists:
        crumbs = [("Home", "/"), ("Lists", "/lists/"), (l["title"], l["url"])]
        top = l["rows"][:3]
        lead = "; ".join(f"{r['rank']}. {r['animal']['commonName']} ({r['display'].split(' (')[0]})" for r in top)
        desc = f"{l['title']}: {lead}. Full ranking of {len(l['rows'])} animals with figures and sources."
        if len(desc) > 158:
            desc = f"{l['title']}: {lead}. Ranked list of {len(l['rows'])} animals."
        render("list.html", l["url"], "lists", 0.7, lst=l, crumbs=crumbs,
               schema=[crumbs_schema(crumbs), itemlist(l["title"], [r["animal"] for r in l["rows"]]),
                       article(l["title"], desc[:158], l["url"])],
               title=f"{l['title']} — Top {len(l['rows'])} Ranked"[:60] if len(l["title"]) < 42 else l["title"][:60],
               description=desc[:158])
    crumbs = [("Home", "/"), ("Lists", "/lists/")]
    render("list_index.html", "/lists/", "lists", 0.6, crumbs=crumbs, schema=[crumbs_schema(crumbs)],
           title="Animal Records & Rankings: Fastest, Heaviest, Oldest",
           description=f"{len(lists)} animal leaderboards: the fastest, heaviest, tallest, longest-living and most endangered animals, ranked with figures for every entry.")

    # ---- fact hubs
    ordered = sorted(animals.values(), key=lambda a: a["commonName"])
    for f in facts:
        crumbs = [("Home", "/"), ("Facts", "/facts/"), (f["column"], f["url"])]
        render("fact.html", f["url"], "lists", 0.6, fact=f, animals=ordered, crumbs=crumbs,
               schema=[crumbs_schema(crumbs), article(f["title"], f["intro"][:150], f["url"])],
               title=f["title"][:60],
               description=(f"{f['column']} for {len(animals)} animals in one sortable chart, from "
                            f"{ordered[0]['commonName'].lower()} to {ordered[-1]['commonName'].lower()}. {f['intro'].split('. ')[0]}.")[:158])
    crumbs = [("Home", "/"), ("Facts", "/facts/")]
    render("fact_index.html", "/facts/", "lists", 0.5, crumbs=crumbs, schema=[crumbs_schema(crumbs)],
           title="Animal Fact Charts: Lifespan, Weight, Size, Speed",
           description=f"Charts of lifespan, weight, size, speed, gestation, diet and conservation status for all {len(animals)} animals in the AnimalStats database.")

    # ---- home, A–Z, search, static pages
    popular = [animals[s] for s in POPULAR if s in animals]
    render("home.html", "/", "pages", 1.0, popular=popular, crumbs=[("Home", "/")],
           schema=[crumbs_schema([("Home", "/")]),
                   {"@context": "https://schema.org", "@type": "WebSite", "name": site["name"], "url": site["url"] + "/",
                    "description": site["tagline"], "publisher": org,
                    "potentialAction": {"@type": "SearchAction",
                                        "target": {"@type": "EntryPoint", "urlTemplate": site["url"] + "/search/?q={search_term_string}"},
                                        "query-input": "required name=search_term_string"}}],
           title="AnimalStats — Animal Facts: Lifespan, Size, Speed & More",
           description=f"Fast facts for {len(animals)} animals: how long they live, how much they weigh, how fast they move, what they eat and their conservation status.")
    letters = OrderedDict()
    for a in ordered:
        letters.setdefault(a["commonName"][0].upper(), []).append(a)
    crumbs = [("Home", "/"), ("All Animals", "/animals/")]
    render("animals.html", "/animals/", "pages", 0.6, letters=letters, crumbs=crumbs,
           schema=[crumbs_schema(crumbs), itemlist("All animals", ordered)],
           title="All Animals A–Z — Facts & Stats Index",
           description=f"A–Z index of all {len(animals)} animals on AnimalStats, each with lifespan, weight, size, speed, diet, habitat and conservation status.")
    crumbs = [("Home", "/"), ("Search", "/search/")]
    render("search.html", "/search/", crumbs=crumbs, schema=[crumbs_schema(crumbs)], noindex=True)
    for slug, name, prio in (("about", "About", 0.3), ("privacy", "Privacy", 0.2)):
        crumbs = [("Home", "/"), (name, f"/{slug}/")]
        render(f"{slug}.html", f"/{slug}/", "pages", prio, crumbs=crumbs, schema=[crumbs_schema(crumbs)])
    render("404.html", "/", filename="404.html", crumbs=[("Home", "/")], schema=[], noindex=True)

    # ---- search index, split sitemaps, housekeeping
    index = [{"n": a["commonName"], "u": a["url"], "c": a["cls"]["name"], "s": a["scientificName"],
              "a": a["aliases"] + [x.lower() for x in a.get("alternateNames", [])],
              "l": a["facts"]["lifespan"]["display"],
              "w": a["facts"]["weight"]["display"].split(" (")[0] if a["facts"].get("weight") else ""} for a in ordered]
    index += [{"n": c["title"], "u": c["url"], "c": "Comparison", "s": "", "a": [], "l": "", "w": ""} for c in comparisons]
    index += [{"n": l["title"], "u": l["url"], "c": "Ranking", "s": "", "a": [], "l": "", "w": ""} for l in lists]
    with open(os.path.join(OUT, "search-index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))

    for group, items in urls.items():
        with open(os.path.join(OUT, f"sitemap-{group}.xml"), "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            for path, prio in sorted(items, key=lambda u: (-u[1], u[0])):
                fh.write(f"<url><loc>{site['url']}{path}</loc><lastmod>{site['updated']}</lastmod>"
                         f"<priority>{prio:.1f}</priority></url>\n")
            fh.write("</urlset>\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for group in urls:
            fh.write(f"<sitemap><loc>{site['url']}/sitemap-{group}.xml</loc><lastmod>{site['updated']}</lastmod></sitemap>\n")
        fh.write("</sitemapindex>\n")
    files = {
        "robots.txt": f"User-agent: *\nAllow: /\nDisallow: /search/\n\nSitemap: {site['url']}/sitemap.xml\n",
        "CNAME": site["domain"] + "\n",
        ".nojekyll": "",
        "site.webmanifest": json.dumps({
            "name": "AnimalStats — Animal Facts & Statistics", "short_name": "AnimalStats", "start_url": "/",
            "display": "standalone", "background_color": "#f8fafc", "theme_color": "#047857",
            "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, indent=2),
    }
    if site.get("adsense_client"):
        files["ads.txt"] = f"google.com, {site['adsense_client'].replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n"
    for name, text in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(text)
    total = sum(len(v) for v in urls.values())
    print(f"{total} indexable pages: {len(animals)} animals, {len(classes)} classes, {len(comparisons)} comparisons, "
          f"{len(lists)} lists, {len(facts)} fact hubs → output/")


if __name__ == "__main__":
    main()
