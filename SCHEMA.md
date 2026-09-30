# Animal record schema — `data/animals/<slug>.json`

`data/master_list.txt` is the source of truth for slug, common name, scientific name, class and search aliases.
`data/wikidata/<slug>.json` is a fetched reference (QID, IUCN status, taxonomy, Wikipedia title, raw quantities).
Validate with `python3 tools/validate.py [files…]`.

```jsonc
{
  "slug": "lion", "commonName": "Lion", "scientificName": "Panthera leo",      // exactly as in the master list
  "alternateNames": ["African lion"],                                           // 0–5
  "nameSingular": "lion", "namePlural": "lions", "article": "a",               // for headings: "How Long Do lions Live?", "How Much Does a lion Weigh?" (keep proper-noun capitals: "African elephant")
  "taxonomy": {"kingdom": "Animalia", "phylum": "Chordata", "class": "Mammalia", "classSlug": "mammals",
               "order": "Carnivora", "family": "Felidae", "genus": "Panthera", "species": "P. leo"},
  "facts": {
    // every fact: min ≤ max (equal when a single figure), fixed unit, human display string with metric AND imperial. null when it genuinely does not apply or no published figure exists (never estimate one yourself). lifespan and height are always required.
    "lifespan":          {"min": 10, "max": 14, "unit": "years", "context": "in the wild", "display": "10–14 years"},   // unit: years|months|weeks|days|hours
    "lifespanCaptivity": {"min": 20, "max": 25, "unit": "years", "context": "in human care", "display": "20–25 years"}, // or null
    "weight":            {"min": 120, "max": 190, "unit": "kg", "context": "adults; males are heavier", "display": "120–190 kg (265–420 lb)"}, // unit: kg|g|mg
    "height":            {"min": 0.9, "max": 1.2, "unit": "m", "label": "Shoulder height", "display": "0.9–1.2 m (3–4 ft)"},  // unit: m|cm|mm; label: Height|Shoulder height|Length|Wingspan|Shell length|Body length
    "speed":             {"min": 80, "max": 80, "unit": "km/h", "verb": "run", "context": "short sprints", "display": "80 km/h (50 mph)"}, // unit km/h only; verb: run|swim|fly|move; null if unknown/sessile
    "gestationPeriod":   {"min": 105, "max": 115, "unit": "days", "label": "Gestation", "display": "about 110 days"}      // unit days only; label: Gestation|Incubation|Egg development; null if not meaningful
  },
  "ecology": {
    "diet": "Carnivore",                 // Carnivore|Herbivore|Omnivore|Insectivore|Piscivore|Filter feeder|Nectarivore|Detritivore|Scavenger
    "dietDetails": "…",                  // 15–45 words: what it actually eats
    "habitat": ["Savanna", "Grassland"], // 1–5 short habitat types
    "range": "…",                        // 8–35 words
    "conservationStatus": "Vulnerable", "iucnCategory": "VU",   // EX|EW|CR|EN|VU|NT|LC|DD|NE, or "DOM" + "Domesticated" for domestic animals
    "populationTrend": "Decreasing",     // Decreasing|Stable|Increasing|Unknown
    "population": "about 23,000 mature individuals"            // optional; only a figure you are confident is a published estimate, else omit
  },
  "description": "…",                    // 60–120 words overview
  "answers": {                           // answer-first paragraphs shown under each question heading. 35–90 words each.
    "lifespan": "…", "weight": "…", "size": "…", "speed": "…", "gestation": "…",   // FIRST SENTENCE ≤ 40 words and directly answers with the numbers.
    "diet": "…", "habitat": "…", "conservation": "…"                               // use null for speed/gestation when that fact is null
  },
  "funFacts": ["…"],                     // 4–6 items, 10–40 words, specific and true
  "relatedAnimals": ["tiger", "leopard"],// 4–6 slugs from the master list
  "appearsInLists": [],                  // leave empty: filled in by build.py
  "faq": [{"question": "…?", "answer": "…"}],   // 4–6; answers 25–80 words, first sentence answers; do not repeat the eight heading questions verbatim
  "meta": {
    "title": "…",                        // ≤ 60 chars, unique
    "description": "…",                  // 110–158 chars, unique, answer-first with the key numbers
    "sources": [{"name": "…", "url": "…"}],  // 2–4, ONLY these URL patterns (see AUTHORING.md)
    "reviewed": "2026-09-30"             // optional YYYY-MM-DD: set when the record's facts or sources change; drives "Reviewed", dateModified and sitemap lastmod (default: site.json "updated")
  }
}
```
