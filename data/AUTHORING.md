# Authoring guide for animal records

Read `SCHEMA.md` and the model record `data/animals/lion.json`. For each animal first read `data/wikidata/<slug>.json`:
use its taxonomy, IUCN status and Wikipedia title as your starting point, and treat its `quantities` as a cross-check only
(Wikidata quantities are sparse and sometimes wrong or for one sex only).

## Accuracy rules
- This is a reference site: every number must be one you are confident appears in authoritative sources (IUCN Red List, Animal Diversity Web,
  AnAge, National Geographic, Smithsonian, NOAA, major zoo and museum species pages, Britannica). Use typical adult ranges, not one-off records;
  mention records in `context`, `answers` or `funFacts` and label them as records.
- Be careful with famous-but-wrong figures. Prefer the conservative, widely supported value and say when estimates vary
  (e.g. sailfish and peregrine speeds, Greenland shark age, "cheetah 120 km/h"). Never invent population numbers; omit `population` unless sure.
- IUCN category must be the current Red List assessment as best you know it; if it differs from the Wikidata file, keep the one you are confident is
  newer and say so in your final report. Domestic animals use `"iucnCategory": "DOM"`, `"conservationStatus": "Domesticated"`, trend `"Stable"`.
- Subspecies/generic pages (Grizzly Bear, Gorilla, Red-Eared Slider): the page covers the named animal; say in the description how it relates to the species.
- Facts that do not apply are `null` (speed of a clam, gestation of an animal with no meaningful figure). Egg layers use label `Incubation`
  (or `Egg development` for fish/amphibians/invertebrates) in `gestationPeriod`. Snakes, fish, whales, lizards use label `Length` in `height`; birds may use
  `Height` or `Wingspan` (pick the one people search; put the other in the size answer). Four-legged mammals use `Shoulder height`.
- Units are fixed (see schema) because leaderboards sort on them: speed always km/h, gestation always days, display strings carry both metric and imperial.

## Voice
- Plain, factual, friendly US English. Lead with the number. No filler, no "fascinating creatures", no invented anecdotes.
- `answers.*`: first sentence ≤ 40 words and answers the heading question on its own (it is written to win a featured snippet). Then 1–3 sentences of context:
  wild vs captivity, males vs females, what limits it, how it compares.
- FAQs must be questions people really search about THIS animal ("Can a … kill a …", "Do … make good pets", "Are … dangerous to humans", "What is a group of … called",
  "What is the difference between a … and a …", "How many … are left"). Don't repeat the eight heading questions.
- `meta.description`: 110–158 chars, answer-first: e.g. "Lions live 10–14 years in the wild, weigh 120–190 kg and sprint at 80 km/h. Diet, habitat, conservation status and more lion facts."
  `meta.title` ≤ 60 chars; vary patterns ("Lion Facts: Lifespan, Size, Speed & Diet", "How Long Do Lions Live? Lion Facts & Stats", …).

## Sources (`meta.sources`) — only these URL patterns, 2–4 per animal
- Wikipedia: `https://en.wikipedia.org/wiki/<Title>` using the `wikipedia` title from the Wikidata file (spaces → underscores)
- IUCN Red List search: `https://www.iucnredlist.org/search?query=<Genus%20species>&searchType=species` (not for domestic animals)
- Animal Diversity Web: `https://animaldiversity.org/accounts/<Genus_species>/`
- AnAge: `https://genomics.senescence.info/species/entry.php?species=<Genus_species>`
- Wikidata: `https://www.wikidata.org/wiki/<QID>`
Do not link anything else, and never fabricate deep links.
