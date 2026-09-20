#!/usr/bin/env python3
"""Fetch reference data from Wikidata (CC0) into data/wikidata/<slug>.json.

Per animal: QID, English Wikipedia title, IUCN status (P141), taxonomy via the parent-taxon chain (P171 + rank P105)
and any measured quantities Wikidata holds (mass, life expectancy, speed, gestation, height, length).
The files are a reference cache for authoring and QA; the site itself is built from data/animals/.
"""
import json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "wikidata")
UA = "animalstats-build/0.1 (https://animalstats.org; info@animalstats.org)"
RANKS = {"Q36732": "kingdom", "Q38348": "phylum", "Q37517": "class", "Q36602": "order", "Q35409": "family",
         "Q34740": "genus", "Q7432": "species"}
PROPS = {"P2067": "mass", "P2250": "lifeExpectancy", "P2052": "speed", "P3063": "gestation", "P2048": "height",
         "P2043": "length"}


def master():
    out, cls = [], None
    for line in open(os.path.join(ROOT, "data", "master_list.txt"), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            cls = line.strip("[]")
            continue
        parts = [p.strip() for p in line.split("|")]
        out.append({"slug": parts[0], "commonName": parts[1], "scientificName": parts[2], "classSlug": cls,
                    "aliases": [a.strip() for a in parts[3].split(",") if a.strip()] if len(parts) > 3 else []})
    return out


def api(**params):
    """Wikidata action API (the SPARQL endpoint times out too often to rely on in a build script)."""
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(dict(params, format="json"))
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            print(f"  retry ({e})", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return {}


IUCN = {"Q211005": "Least Concern", "Q719675": "Near Threatened", "Q278113": "Vulnerable", "Q11394": "Endangered",
        "Q219127": "Critically Endangered", "Q239509": "Extinct in the Wild", "Q237350": "Extinct",
        "Q3245245": "Data Deficient", "Q96377276": "Endangered"}
UNITS = {"Q11570": "kg", "Q41803": "g", "Q191118": "t", "Q100995": "lb", "Q577": "year", "Q5151": "month",
         "Q23387": "week", "Q573": "day", "Q180154": "km/h", "Q211256": "mph", "Q182429": "m/s", "Q11573": "m",
         "Q174728": "cm", "Q174789": "mm", "Q3710": "ft", "Q218593": "in"}


def entity_ids(claims, prop):
    out = []
    for c in claims.get(prop, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and "id" in v:
            out.append((v["id"], c.get("rank")))
    out.sort(key=lambda x: x[1] != "preferred")
    return [i for i, _ in out]


def get_entities(ids, props="claims|sitelinks"):
    got = {}
    ids = list(ids)
    for i in range(0, len(ids), 50):
        r = api(action="wbgetentities", ids="|".join(ids[i:i + 50]), props=props, sitefilter="enwiki")
        got.update(r.get("entities", {}))
        time.sleep(0.5)
    return got


def main():
    os.makedirs(OUT, exist_ok=True)
    animals = master()
    cache_path = os.path.join(OUT, "_qids.json")
    qids = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    for a in animals:
        if a["slug"] in qids:
            continue
        r = api(action="query", list="search", srsearch=f'haswbstatement:"P225={a["scientificName"]}"', srlimit=3)
        hits = [h["title"] for h in r.get("query", {}).get("search", [])]
        qids[a["slug"]] = hits[0] if hits else None
        print(f"  {a['slug']}: {qids[a['slug']]}")
        time.sleep(0.3)
        json.dump(qids, open(cache_path, "w"), indent=1)
    ents = get_entities({q for q in qids.values() if q})

    # Walk the parent-taxon chain level by level, batching every animal's current ancestor together.
    tax = {}          # qid -> (rankQid, taxonName, parentQid)
    frontier = {q for q in qids.values() if q}
    for _ in range(45):
        need = [q for q in frontier if q not in tax]
        if not need:
            break
        got = ents if _ == 0 else get_entities(need, props="claims")
        nxt = set()
        for q in need:
            c = got.get(q, {}).get("claims", {})
            name = (c.get("P225", [{}])[0].get("mainsnak", {}).get("datavalue", {}) or {}).get("value")
            rank = (entity_ids(c, "P105") or [None])[0]
            parent = (entity_ids(c, "P171") or [None])[0]
            tax[q] = (rank, name, parent)
            if parent:
                nxt.add(parent)
        frontier = nxt

    for a in animals:
        q = qids.get(a["slug"])
        rec = dict(a, qid=q)
        if q and q in ents:
            e = ents[q]
            c = e.get("claims", {})
            status = (entity_ids(c, "P141") or [None])[0]
            rec["iucnStatus"] = IUCN.get(status, status)
            rec["wikipedia"] = e.get("sitelinks", {}).get("enwiki", {}).get("title")
            rec["taxonomy"], cur, hops = {}, q, 0
            while cur and cur in tax and hops < 60:
                rank, name, parent = tax[cur]
                if rank in RANKS and name:
                    rec["taxonomy"].setdefault(RANKS[rank], name)
                cur, hops = parent, hops + 1
            rec["quantities"] = []
            for prop, label in PROPS.items():
                for st in c.get(prop, []):
                    v = st.get("mainsnak", {}).get("datavalue", {}).get("value")
                    if not isinstance(v, dict) or "amount" not in v:
                        continue
                    unit = v.get("unit", "").rsplit("/", 1)[-1]
                    quals = st.get("qualifiers", {})
                    sex = [x["datavalue"]["value"]["id"] for x in quals.get("P21", []) if "datavalue" in x]
                    rec["quantities"].append({"property": label, "amount": v["amount"].lstrip("+"),
                                              "unit": UNITS.get(unit, unit),
                                              "sex": {"Q44148": "male", "Q43445": "female"}.get(sex[0], sex[0]) if sex else None})
        with open(os.path.join(OUT, a["slug"] + ".json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
    found = sum(1 for a in animals if qids.get(a["slug"]))
    print(f"{found}/{len(animals)} matched on Wikidata")


if __name__ == "__main__":
    main()
