# AnimalStats — animalstats.org

Animal facts database: lifespan, weight, size, speed, gestation, diet, habitat and IUCN status, one page per animal,
plus class hubs, comparisons, leaderboards and fact charts. Static site: JSON data → Python + Jinja2 → `output/` → GitHub Pages.

**Live:** https://animalstats.org · **Contact:** info@animalstats.org

## Layout

| Path | What |
| --- | --- |
| `data/master_list.txt` | Source of truth: slug, common name, scientific name, class, search aliases |
| `data/animals/<slug>.json` | One record per animal — schema in `SCHEMA.md`, writing and accuracy rules in `data/AUTHORING.md` |
| `data/wikidata/<slug>.json` | Reference cache fetched by `tools/fetch_wikidata.py` (QID, taxonomy, IUCN status, Wikipedia title, raw quantities) |
| `data/comparisons.json` + `data/comparisons/<slug>.json` | Comparison pairs and their editorial text (the data table is generated) |
| `data/lists.json`, `data/facts.json`, `data/classes.json` | Leaderboard, fact-hub and class definitions with intro copy |
| `data/site.json` | Domain, AdSense client, GA4 id, Ahrefs key, ad slot ids — every tag renders only when its id is set |
| `templates/`, `static/`, `icons/` | Jinja2 templates, JS/favicons/OG card, the Lucide SVGs inlined at build time (ISC) |
| `build.py` | Generator → `output/` (git-ignored) |
| `tools/validate.py` | Data validator: schema, fixed units, word limits, answer-first rule, source URL whitelist, Wikidata cross-check (`-w` lists warnings) |
| `tools/check_site.py` | Output checker: links, JSON-LD, canonicals, split sitemaps, tag order, unique titles/descriptions, 6-stat card above any ad |

## URLs

`/animals/<slug>/` · `/mammals/` `/birds/` `/reptiles/` `/amphibians/` `/fish/` `/invertebrates/` · `/compare/<a>-vs-<b>/` ·
`/lists/<topic>/` · `/facts/<type>/` · `/animals/` (A–Z) · `/search/?q=` (noindex; target of the WebSite SearchAction) ·
`sitemap.xml` is an index of `sitemap-animals.xml`, `sitemap-compare.xml`, `sitemap-lists.xml`, `sitemap-pages.xml`.

## Build

```
pip install -r requirements.txt
npm install                     # only to recompile Tailwind after changing classes
python3 tools/fetch_wikidata.py # optional: refresh the Wikidata reference cache (action API; SPARQL endpoint proved unreliable)
python3 tools/validate.py -w
python3 build.py                # compiles Tailwind when node_modules exists, writes output/
python3 tools/check_site.py
```

Leaderboards, `appearsInLists`, comparison tables and fact charts are all computed from the animal records, so fixing a
number in one JSON file updates every page that uses it. Facts use fixed units (years/months/…, kg/g/mg, m/cm/mm, km/h, days)
so rankings sort correctly; display strings carry metric and imperial.

## Data policy

Taxonomy and IUCN category are cross-checked against Wikidata (CC0). Lifespan, size, speed and gestation figures are typical
adult ranges compiled from IUCN, Animal Diversity Web, AnAge and comparable references — Wikidata's own quantities are too
sparse and error-prone to publish directly (e.g. a cheetah "mass" of 275 g, which is a birth weight). A fact with no
published figure is `null`, never an estimate. Source links are restricted to a whitelist of URL patterns.

## Performance, analytics, ads

Tailwind is compiled (~20 KB) and inlined; Lucide icons are inlined SVG; no web fonts; the search index loads on first focus.
`templates/base.html` emits Consent Mode v2 defaults inline (denied for EEA + UK + CH, granted elsewhere), then the static
Google tag (`gtag.js` + config, without re-declaring `dataLayer`/`gtag`), then a loader that injects AdSense and Ahrefs after
the `load` event (AdSense is the only tag heavy enough to hurt Lighthouse). Each renders only if configured in `data/site.json`.
With these defaults and no consent banner, EEA/UK/CH visitors send only consent-denied pings (`gcs=G100`) that GA4 reports do not show.
In-article ad units
(after the third question section and before related animals; never above the quick-facts card) render once `ad_slots` are set.

## Deploy

`.github/workflows/deploy.yml`: validate → build with the committed CSS → check → publish `output/` to GitHub Pages on push to `main`.
After adding new Tailwind classes run `npm install && python3 build.py` and commit `static/css/site.css`.
