#!/usr/bin/env python3
"""Validate animal records.  Usage: python3 tools/validate.py [file.json …]   (no args = all + coverage + Wikidata cross-check)"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANIMALS = os.path.join(ROOT, "data", "animals")
CLASSES = {"mammals": "Mammalia", "birds": "Aves", "reptiles": "Reptilia", "amphibians": "Amphibia"}
IUCN = {"EX": "Extinct", "EW": "Extinct in the Wild", "CR": "Critically Endangered", "EN": "Endangered", "VU": "Vulnerable",
        "NT": "Near Threatened", "LC": "Least Concern", "DD": "Data Deficient", "NE": "Not Evaluated", "DOM": "Domesticated"}
DIETS = {"Carnivore", "Herbivore", "Omnivore", "Insectivore", "Piscivore", "Filter feeder", "Nectarivore", "Detritivore", "Scavenger"}
UNITS = {"lifespan": {"years", "months", "weeks", "days", "hours"}, "lifespanCaptivity": {"years", "months", "weeks", "days", "hours"},
         "weight": {"kg", "g", "mg"}, "height": {"m", "cm", "mm"}, "speed": {"km/h"}, "gestationPeriod": {"days"}}
LABELS = {"height": {"Height", "Shoulder height", "Length", "Wingspan", "Shell length", "Body length"},
          "gestationPeriod": {"Gestation", "Incubation", "Egg development"}}
SOURCE_OK = re.compile(r"^https://(en\.wikipedia\.org/wiki/[^ ]+|www\.iucnredlist\.org/search\?query=[^ ]+&searchType=species|"
                       r"animaldiversity\.org/accounts/[A-Za-z_]+/|genomics\.senescence\.info/species/entry\.php\?species=[A-Za-z_]+|"
                       r"www\.wikidata\.org/wiki/Q\d+)$")
ANSWER_KEYS = ["lifespan", "weight", "size", "speed", "gestation", "diet", "habitat", "conservation"]


def master():
    out, cls = {}, None
    for line in open(os.path.join(ROOT, "data", "master_list.txt"), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            cls = line.strip("[]")
            continue
        p = [x.strip() for x in line.split("|")]
        out[p[0]] = {"commonName": p[1], "scientificName": p[2], "classSlug": cls}
    return out


def words(s):
    return len((s or "").split())


def first_sentence(s):
    return re.split(r"(?<=[.!?])\s", s.strip(), maxsplit=1)[0]


def check(path, M):
    errs, warns = [], []
    E = errs.append
    try:
        d = json.load(open(path, encoding="utf-8"))
    except ValueError as e:
        return [f"invalid JSON: {e}"], [], None
    slug = os.path.basename(path)[:-5]
    m = M.get(slug)
    if d.get("slug") != slug:
        E("slug does not match filename")
    if not m:
        E("slug not in master_list.txt")
    else:
        for k in ("commonName", "scientificName"):
            if d.get(k) != m[k]:
                E(f"{k} {d.get(k)!r} != master {m[k]!r}")
        if d.get("taxonomy", {}).get("classSlug") != m["classSlug"]:
            E(f"taxonomy.classSlug must be {m['classSlug']!r}")
    for k in ("nameSingular", "namePlural"):
        if not d.get(k):
            E(f"missing {k}")
    if d.get("article") not in ("a", "an"):
        E("article must be 'a' or 'an'")
    if len(d.get("alternateNames", [])) > 5:
        E("alternateNames: max 5")
    t = d.get("taxonomy", {})
    for k in ("kingdom", "phylum", "class", "classSlug", "order", "family", "genus", "species"):
        if not t.get(k):
            E(f"taxonomy.{k} missing")
    if m and t.get("classSlug") in CLASSES and t.get("class") != CLASSES[t["classSlug"]]:
        E(f"taxonomy.class should be {CLASSES[t['classSlug']]}")
    if t.get("genus") and d.get("scientificName") and t["genus"] != d["scientificName"].split()[0]:
        E("taxonomy.genus does not match scientificName")

    facts = d.get("facts", {})
    for key, units in UNITS.items():
        if key not in facts:
            E(f"facts.{key} missing (use null if not applicable)")
            continue
        f = facts[key]
        if f is None:
            if key in ("lifespan", "height"):
                E(f"facts.{key} may not be null")
            continue
        for n in ("min", "max"):
            if not isinstance(f.get(n), (int, float)) or f[n] <= 0:
                E(f"facts.{key}.{n} must be a positive number")
        if isinstance(f.get("min"), (int, float)) and isinstance(f.get("max"), (int, float)) and f["min"] > f["max"]:
            E(f"facts.{key}: min > max")
        if f.get("unit") not in units:
            E(f"facts.{key}.unit {f.get('unit')!r} not in {sorted(units)}")
        if not f.get("display") or not re.search(r"\d", f["display"]):
            E(f"facts.{key}.display missing or has no number")
        if key in LABELS and f.get("label") not in LABELS[key]:
            E(f"facts.{key}.label {f.get('label')!r} not in {sorted(LABELS[key])}")
        if key == "speed" and f.get("verb") not in ("run", "swim", "fly", "move"):
            E("facts.speed.verb must be run|swim|fly|move")
        if key in ("weight", "height", "speed") and "(" not in f.get("display", ""):
            E(f"facts.{key}.display needs metric and imperial, e.g. '120–190 kg (265–420 lb)'")
    sp = facts.get("speed")
    if sp and isinstance(sp.get("max"), (int, float)) and sp["max"] > 400:
        E("speed over 400 km/h is not plausible")

    eco = d.get("ecology", {})
    if eco.get("diet") not in DIETS:
        E(f"ecology.diet {eco.get('diet')!r} not in {sorted(DIETS)}")
    if not 12 <= words(eco.get("dietDetails")) <= 50:
        E(f"ecology.dietDetails {words(eco.get('dietDetails'))} words (15–45)")
    if not 1 <= len(eco.get("habitat", [])) <= 5:
        E("ecology.habitat: 1–5 items")
    if not 6 <= words(eco.get("range")) <= 40:
        E(f"ecology.range {words(eco.get('range'))} words (8–35)")
    cat = eco.get("iucnCategory")
    if cat not in IUCN:
        E(f"ecology.iucnCategory {cat!r} invalid")
    elif eco.get("conservationStatus") != IUCN[cat]:
        E(f"ecology.conservationStatus should be {IUCN[cat]!r} for {cat}")
    if eco.get("populationTrend") not in ("Decreasing", "Stable", "Increasing", "Unknown"):
        E("ecology.populationTrend invalid")

    if not 55 <= words(d.get("description")) <= 130:
        E(f"description {words(d.get('description'))} words (60–120)")
    ans = d.get("answers", {})
    for k in ANSWER_KEYS:
        a = ans.get(k)
        if a is None:
            fact = {"speed": "speed", "gestation": "gestationPeriod", "weight": "weight"}.get(k)
            if not fact or facts.get(fact) is not None:
                E(f"answers.{k} missing")
            continue
        if not 30 <= words(a) <= 95:
            E(f"answers.{k} {words(a)} words (35–90)")
        if words(first_sentence(a)) > 40:
            E(f"answers.{k}: first sentence is {words(first_sentence(a))} words (≤ 40)")
    for k, fact in (("speed", "speed"), ("gestation", "gestationPeriod"), ("weight", "weight")):
        if facts.get(fact) is None and ans.get(k):
            E(f"answers.{k} given but facts.{fact} is null")
    ff = d.get("funFacts", [])
    if not 4 <= len(ff) <= 6:
        E(f"funFacts: need 4–6, got {len(ff)}")
    for x in ff:
        if not 8 <= words(x) <= 45:
            E(f"funFact {words(x)} words (10–40): {x[:40]}…")
    rel = d.get("relatedAnimals", [])
    if not 4 <= len(rel) <= 6 or slug in rel or len(set(rel)) != len(rel):
        E("relatedAnimals: 4–6 unique slugs, not self")
    for r in rel:
        if r not in M:
            E(f"relatedAnimals: unknown slug {r!r}")
    faq = d.get("faq", [])
    if not 4 <= len(faq) <= 6:
        E(f"faq: need 4–6, got {len(faq)}")
    for q in faq:
        if not q.get("question", "").endswith("?"):
            E(f"faq question must end with '?': {q.get('question')!r}")
        if not 22 <= words(q.get("answer")) <= 85:
            E(f"faq answer {words(q.get('answer'))} words (25–80): {q.get('question')}")
    meta = d.get("meta", {})
    if not 20 <= len(meta.get("title", "")) <= 60:
        E(f"meta.title {len(meta.get('title', ''))} chars (≤ 60)")
    if not 110 <= len(meta.get("description", "")) <= 158:
        E(f"meta.description {len(meta.get('description', ''))} chars (110–158)")
    src = meta.get("sources", [])
    if not 2 <= len(src) <= 4:
        E("meta.sources: 2–4 items")
    for s in src:
        if not s.get("name") or not SOURCE_OK.match(s.get("url", "")):
            E(f"meta.sources: URL not in an allowed pattern: {s.get('url')!r}")
    if re.search(r"\d\s?-\s?\d+ ?(years|kg|km/h|days|m\b|cm|lb|mph)", json.dumps(d, ensure_ascii=False)):
        E("use an en dash (–) in number ranges, not a hyphen")

    wd_path = os.path.join(ROOT, "data", "wikidata", slug + ".json")
    if os.path.exists(wd_path) and cat in IUCN:
        wd = json.load(open(wd_path, encoding="utf-8"))
        if wd.get("iucnStatus") and cat != "DOM" and wd["iucnStatus"] != IUCN[cat]:
            warns.append(f"IUCN: record says {IUCN[cat]}, Wikidata says {wd['iucnStatus']}")
        for rank in ("order", "family"):
            w = (wd.get("taxonomy") or {}).get(rank)
            if w and t.get(rank) and w != t[rank]:
                warns.append(f"taxonomy.{rank}: record {t[rank]}, Wikidata {w}")
    return errs, warns, d


def main():
    M = master()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    paths = args or sorted(os.path.join(ANIMALS, f) for f in os.listdir(ANIMALS) if f.endswith(".json"))
    total, titles, descs, all_warns = 0, {}, {}, []
    for p in paths:
        errs, warns, d = check(p, M)
        if d:
            for store, val, kind in ((titles, d.get("meta", {}).get("title"), "title"),
                                     (descs, d.get("meta", {}).get("description"), "description")):
                if val in store:
                    errs.append(f"duplicate meta.{kind} with {store[val]}")
                store[val] = os.path.basename(p)
        for e in errs:
            print(f"{os.path.basename(p)}: {e}")
        all_warns += [f"{os.path.basename(p)}: {w}" for w in warns]
        total += len(errs)
    if all_warns and (args or "-w" in sys.argv):
        print("warnings (check, not fatal):")
        for w in all_warns:
            print("  ", w)
    if not args:
        have = {os.path.basename(p)[:-5] for p in paths}
        missing = [s for s in M if s not in have]
        print(f"{len(have)}/{len(M)} animals present; missing {len(missing)}; {len(all_warns)} Wikidata warnings (-w to list)")
        if missing:
            print("  missing:", ", ".join(missing[:50]), "…" if len(missing) > 50 else "")
    print(f"{len(paths)} files checked, {total} errors")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
