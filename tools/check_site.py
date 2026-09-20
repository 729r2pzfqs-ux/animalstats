#!/usr/bin/env python3
"""Validate output/: links, JSON-LD, canonicals, split sitemaps, tag order, unique titles/descriptions, page structure."""
import json, os, re, sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
SITE = "https://animalstats.org"
errors, n, titles, descs = [], 0, {}, {}
index = open(os.path.join(OUT, "sitemap.xml")).read()
parts = re.findall(r"<loc>" + re.escape(SITE) + r"/(sitemap-[a-z]+\.xml)</loc>", index)
if len(parts) < 3:
    errors.append("sitemap.xml should be an index of split sitemaps")
sitemap = set()
for p in parts:
    sitemap |= set(re.findall(r"<loc>" + re.escape(SITE) + r"(/[^<]*)</loc>", open(os.path.join(OUT, p)).read()))
for root, _, files in os.walk(OUT):
    for f in files:
        if not f.endswith(".html"):
            continue
        html = open(os.path.join(root, f), encoding="utf-8").read()
        rel = "/" + os.path.relpath(root, OUT).replace(".", "").strip("/")
        rel = rel if rel.endswith("/") else rel + "/"
        n += 1
        for href in set(re.findall(r'(?:href|src)="(/[^"#?]*)', html)):
            t = os.path.join(OUT, href.lstrip("/"))
            if not (os.path.isfile(t) or os.path.isfile(os.path.join(t, "index.html"))):
                errors.append(f"{rel}: broken link {href}")
        types = []
        for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try:
                types.append(json.loads(b).get("@type"))
            except ValueError as e:
                errors.append(f"{rel}: bad JSON-LD {e}")
        c, a, g, h = (html.find(x) for x in ("gtag('consent', 'default'", "adsbygoogle.js", "googletagmanager.com/gtag/js", "analytics.ahrefs.com"))
        order = [x for x in (c, a, g, h) if x > 0]
        if c < 0 or order != sorted(order):
            errors.append(f"{rel}: consent → AdSense → gtag → Ahrefs order wrong")
        if html.count("window.dataLayer = window.dataLayer") != 1:
            errors.append(f"{rel}: dataLayer declared {html.count('window.dataLayer = window.dataLayer')} times")
        noindex = 'name="robots" content="noindex"' in html
        if f != "index.html" or noindex:
            continue
        canon = re.search(r'<link rel="canonical" href="' + re.escape(SITE) + r'([^"]*)"', html)
        if not canon or canon.group(1) != rel:
            errors.append(f"{rel}: canonical mismatch")
        if rel not in sitemap:
            errors.append(f"{rel}: not in any sitemap")
        if "BreadcrumbList" not in types:
            errors.append(f"{rel}: no BreadcrumbList")
        if rel == "/" and '"SearchAction"' not in html:
            errors.append("/: WebSite SearchAction missing")
        if rel.startswith("/animals/") and rel != "/animals/":
            if "FAQPage" not in types:
                errors.append(f"{rel}: no FAQPage schema")
            card, first_ad = html.find('aria-label="Quick facts"'), html.find("ad placement")
            if card < 0 or (0 < first_ad < card):
                errors.append(f"{rel}: quick-facts card missing or below an ad")
            if html.count('class="stat"') != 6:
                errors.append(f"{rel}: quick-facts card has {html.count('class=\"stat\"')} stats, expected 6")
        if rel.startswith("/compare/") and rel != "/compare/" and "FAQPage" not in types:
            errors.append(f"{rel}: no FAQPage schema")
        if html.count("<h1") != 1:
            errors.append(f"{rel}: {html.count('<h1')} h1 tags")
        t = re.search(r"<title>(.*?)</title>", html).group(1)
        d = re.search(r'<meta name="description" content="(.*?)"', html).group(1)
        if not 50 <= len(d.replace("&amp;", "&")) <= 165:
            errors.append(f"{rel}: description length {len(d)}")
        for store, v, kind in ((titles, t, "title"), (descs, d, "description")):
            if v in store:
                errors.append(f"{rel}: duplicate {kind} with {store[v]}")
            store[v] = rel
print(f"checked {n} html files, {len(sitemap)} sitemap urls in {len(parts)} sitemaps, {len(errors)} errors")
for e in errors[:40]:
    print("  ", e)
sys.exit(1 if errors else 0)
