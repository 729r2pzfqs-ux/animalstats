#!/usr/bin/env python3
"""Validate output/: links, JSON-LD, canonicals, flat sitemap, tag order, unique titles/descriptions, page structure."""
import json, os, re, sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
SITE = "https://animalstats.org"
errors, n, titles, descs = [], 0, {}, {}
GA4_REQUIRED = bool(json.load(open(os.path.join(os.path.dirname(OUT), "data", "site.json"))).get("ga4_id"))
smap = open(os.path.join(OUT, "sitemap.xml")).read()
if "<urlset" not in smap or "<sitemapindex" in smap:
    errors.append("sitemap.xml should be a single flat <urlset>")
locs = re.findall(r"<loc>" + re.escape(SITE) + r"(/[^<]*)</loc>", smap)
if len(locs) != len(set(locs)):
    errors.append("sitemap.xml has duplicate URLs")
sitemap = set(locs)
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
        c = html.find("gtag('consent', 'default'")
        g = html.find('<script async src="https://www.googletagmanager.com/gtag/js?id=')
        cfg, a = html.find("gtag('config', '"), html.find("adsbygoogle.js")
        if c < 0 or (a > 0 and a < c):
            errors.append(f"{rel}: consent defaults must come before AdSense")
        if g > 0 and not (c < g < cfg):
            errors.append(f"{rel}: expected consent defaults → static gtag.js → gtag config")
        if GA4_REQUIRED and g < 0:
            errors.append(f"{rel}: static gtag.js tag missing")
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
print(f"checked {n} html files, {len(sitemap)} sitemap urls, {len(errors)} errors")
for e in errors[:40]:
    print("  ", e)
sys.exit(1 if errors else 0)
