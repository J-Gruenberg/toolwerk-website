#!/usr/bin/env python3
"""Baut tool-werk.de nach site/.

Quellen: src/home_body.html (Startseite aus dem Design-Canvas), src/content.py (Unterseiten),
src/legal/*.html (Rechtstexte), src/base.css + src/pages.css (Stile).
Aufruf: python3 src/build.py   (braucht beautifulsoup4, pillow, playwright mit Chromium)
"""
import hashlib, html, json, re, shutil, sys
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / 'src', ROOT / 'site'
sys.path.insert(0, str(SRC))
from content import PAGES, PRESS  # noqa: E402

SITE = 'https://www.tool-werk.de'
TODAY = date.today().isoformat()
CAL_CTA = 'Meinen Ablauf prüfen lassen →'
IMG = OUT / 'assets' / 'img'
BY_SLUG = {p['slug']: p for p in PAGES}
TEASER = {
    'digitale-mitarbeiter': 'Was ein digitaler Mitarbeiter ist und welche Aufgaben er übernimmt.',
    'zuschlagsfinder': 'Jeden Morgen die öffentlichen Ausschreibungen, die zu Ihnen passen.',
    'pruefaehig': 'Aufmaß und Leistungsnachweis aus Fotos und Sprache.',
    'guard': 'Betriebsanweisungen und Gefährdungsbeurteilungen per QR-Code.',
    'personalportal': 'Unterlagen, Fristen und Zuständigkeiten Ihrer Mitarbeiter an einem Ort.',
    'angebote-kalkulieren': 'Mengen und Positionen vorbereitet, Sie prüfen nur noch.',
    'ueber-uns': 'Wer hinter toolwerk steht.',
}
LEISTUNGEN = ['digitale-mitarbeiter', 'zuschlagsfinder', 'pruefaehig', 'guard', 'personalportal', 'angebote-kalkulieren']

ICONS = {
    'target': 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8z',
    'folder': 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',
    'folder-x': 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM10 11l4 4M14 11l-4 4',
    'check': 'M5 12l4 4L19 6',
    'trend': 'M3 17l6-6 4 4 8-8M15 7h6v6',
    'ruler': 'M3 17L17 3l4 4L7 21zM7 13l2 2M10 10l2 2M13 7l2 2',
    'shield': 'M12 3l8 3v6c0 5-3.5 8-8 9c-4.5-1-8-4-8-9V6z',
    'users': 'M9 11a4 4 0 1 0 0-8a4 4 0 0 0 0 8zM2 21v-1a6 6 0 0 1 12 0v1M16 3.5a4 4 0 0 1 0 7M22 21v-1a6 6 0 0 0-4-5.6',
    'server': 'M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01',
    'lock': 'M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4',
    'search-x': 'M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14zM20 20l-3.5-3.5M8 8l6 6M14 8l-6 6',
    'clock': 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM12 7v5l3 3',
    'calendar': 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
    'euro': 'M17 6a7 7 0 1 0 0 12M5 10h9M5 14h9',
    'file-x': 'M14 3H6v18h12V7zM14 3v4h4M9.5 11.5l5 5M14.5 11.5l-5 5',
    'alert': 'M12 3l10 18H2zM12 10v4M12 17h.01',
    'chart': 'M4 20V10M10 20V4M16 20v-7M22 20H2',
}


def icon(name):
    return f'<span class="tw-icon"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="{ICONS[name]}"/></svg></span>'


def strip(s):
    return re.sub(r'<[^>]+>', '', s)


def url(slug):
    return SITE + ('/' if slug in ('', 'home') else '/' + slug)


def cta_href(task):
    return '/?aufgabe=' + task.replace(' ', '+') + '#check' if task else '/#check'


# ------------------------------------------------------------------ Bilder
def responsive_images():
    """Kleinere Varianten für Handy und Tablet anlegen (nur wenn noch nicht da)."""
    targets = {'hero-garkisch-leitungsgraben': 960, 'jonas-gruenberg-portraet': 600, 'alume-maik-duering-jonas-lkw': 800}
    for f in IMG.glob('garkisch-*.webp'):
        if not re.search(r'-\d+$', f.stem):
            targets[f.stem] = 800
    for stem, w in targets.items():
        src, dst = IMG / f'{stem}.webp', IMG / f'{stem}-{w}.webp'
        if src.exists() and not dst.exists():
            im = Image.open(src)
            im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(dst, 'WEBP', quality=76, method=6)
    # Kunden- und Presselogos werden höchstens 48 px hoch gezeigt: auf doppelte Höhe verkleinern
    for f in list(IMG.glob('kunde-*.webp')) + list(IMG.glob('presse-*.webp')):
        im = Image.open(f)
        if im.height > 100:
            im.resize((round(im.width * 96 / im.height), 96), Image.LANCZOS).save(f, 'WEBP', quality=88, method=6)
    return targets


def srcset(stem, small):
    im = Image.open(IMG / f'{stem}.webp')
    return f'/assets/img/{stem}-{small}.webp {small}w, /assets/img/{stem}.webp {im.width}w', im.width, im.height


# ------------------------------------------------------------------ gemeinsame Teile
def head(title, desc, path, og, jsonld, robots='index, follow, max-image-preview:large', extra=''):
    canon = SITE + path
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#ffffff">
<meta name="author" content="Grünberg Solutions GmbH">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.png" type="image/png" sizes="64x64">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="/assets/fonts/plus-jakarta-sans-latin.woff2" as="font" type="font/woff2" crossorigin>
{extra}<link rel="stylesheet" href="/assets/css/site.css">
<meta property="og:type" content="website">
<meta property="og:locale" content="de_DE">
<meta property="og:site_name" content="toolwerk">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{html.escape(title)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False, separators=(',', ':'))}</script>
</head>
"""


def nav(current='', home=False):
    links = [('Digitale Mitarbeiter', '/digitale-mitarbeiter', 'digitale-mitarbeiter'),
             ('Zuschlagsfinder', '/zuschlagsfinder', 'zuschlagsfinder'),
             ('Beispiele', '#beispiele' if home else '/#beispiele', ''),
             ('Über uns', '/ueber-uns', 'ueber-uns')]
    items = ''
    for t, h, s in links:
        on = bool(s) and s == current
        cur = ' aria-current="page"' if on else ''
        col = '#1c3d9b' if on else '#0b1428'
        items += f'<a href="{h}"{cur} style="text-decoration: none; color: {col};">{t}</a>'

    check = '#check' if home else '/#check'
    return f"""<div style="position: sticky; top: 12px; z-index: 30; padding-inline: 16px; margin-top: 12px;">
<nav aria-label="Hauptnavigation" style="max-width: 1080px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 8px 8px 8px 22px; background: rgba(255,255,255,0.95); border: 1px solid #e1e6ef; border-radius: 999px; box-shadow: 0 8px 30px rgba(10,26,60,0.10);">
<a aria-label="toolwerk Startseite" href="/" style="display: flex; align-items: center; flex: 0 0 auto;"><img alt="toolwerk" decoding="async" height="284" src="/assets/img/toolwerk-logo.svg" style="height: 26px; width: auto; display: block;" width="1366"></a>
<div class="tw-nav-links" style="display: flex; gap: 26px; font-size: 14px; font-weight: 600;">{items}</div>
<a class="tw-nav-cta" href="{check}" style="display: inline-flex; align-items: center; height: 42px; padding: 0 20px; border-radius: 999px; background: #c5301f; color: #ffffff; font-size: 14px; font-weight: 700; text-decoration: none; white-space: nowrap;">Ablauf prüfen lassen</a>
</nav>
</div>"""


def footer(home=False):
    leist = ''.join(f'<li><a href="/{s}">{BY_SLUG[s]["nav"]}</a></li>' for s in LEISTUNGEN)
    check = '#check' if home else '/#check'
    fragen = '#fragen' if home else '/#fragen'
    return f"""<footer class="tw-foot"><div class="tw-wrap">
<div class="tw-foot-grid">
<div><a href="/" aria-label="toolwerk Startseite"><img src="/assets/img/toolwerk-logo.svg" alt="toolwerk" width="1366" height="284" loading="lazy" style="height: 24px; width: auto; display: block; margin-bottom: 16px;"></a>
<p>Digitale Mitarbeiter für Bau und Handwerk. Wir übernehmen die Arbeit, die bei Ihnen liegen bleibt.</p>
<p style="margin-top: 10px;">toolwerk ist eine Marke der Grünberg Solutions GmbH.</p></div>
<div><h2>Leistungen</h2><ul>{leist}</ul></div>
<div><h2>Unternehmen</h2><ul><li><a href="/ueber-uns">Über uns</a></li><li><a href="{check}">Kennenlernen vereinbaren</a></li><li><a href="{fragen}">Häufige Fragen</a></li><li><a href="/impressum">Impressum</a></li><li><a href="/datenschutz">Datenschutz</a></li></ul></div>
<div><h2>Kontakt</h2><address>Grünberg Solutions GmbH<br>Großer Markt 16<br>19348 Perleberg</address>
<ul style="margin-top: 12px;"><li><a href="tel:+4915255604258">+49 152 55604258</a></li><li><a href="mailto:kontakt@gruenbergsolutions.de">kontakt@gruenbergsolutions.de</a></li></ul></div>
</div>
<div class="tw-foot-bottom"><span>© {date.today().year} Grünberg Solutions GmbH</span><span><a href="/impressum">Impressum</a> · <a href="/datenschutz">Datenschutz</a></span></div>
</div></footer>"""


def cta_panel(task):
    return f"""<section class="tw-sec tw-sec--tight"><div class="tw-wrap"><div class="tw-panel tw-stack tw-center" style="text-align: center;">
<p class="tw-eyebrow">Ablauf-Check</p>
<h2 class="tw-h2">Welche Arbeit soll bei Ihnen <span class="tw-blue">nicht noch ein Jahr liegen bleiben?</span></h2>
<p class="tw-lead">Im ersten Gespräch schauen wir uns Ihren Ablauf an. <b>Persönlich, bei Ihnen im Betrieb oder per Video.</b></p>
<div class="tw-btns"><a class="tw-btn" href="{cta_href(task)}">{CAL_CTA}</a></div>
</div></div></section>"""


# ------------------------------------------------------------------ Schema.org
ORG = {
    '@type': 'Organization', '@id': SITE + '/#org', 'name': 'toolwerk', 'url': SITE + '/',
    'logo': {'@type': 'ImageObject', 'url': SITE + '/assets/img/toolwerk-logo-quadrat.png', 'width': 512, 'height': 512},
    'image': SITE + '/og.jpg',
    'description': 'Digitale Mitarbeiter für Bau und Handwerk: KI, die eine feste Aufgabe im Betrieb übernimmt und alles zur Freigabe vorlegt.',
    'slogan': 'Wir übernehmen die Arbeit, die bei Ihnen liegen bleibt.',
    'parentOrganization': {'@type': 'Organization', 'name': 'Grünberg Solutions GmbH', 'url': 'https://www.gruenbergsolutions.de/'},
    'address': {'@type': 'PostalAddress', 'streetAddress': 'Großer Markt 16', 'postalCode': '19348', 'addressLocality': 'Perleberg', 'addressRegion': 'Brandenburg', 'addressCountry': 'DE'},
    'telephone': '+49 152 55604258', 'email': 'kontakt@gruenbergsolutions.de',
    'founder': {'@type': 'Person', '@id': SITE + '/ueber-uns#jonas', 'name': 'Jonas Grünberg'},
    'areaServed': {'@type': 'Country', 'name': 'Deutschland'},
    'knowsAbout': ['Digitale Mitarbeiter', 'Künstliche Intelligenz im Handwerk', 'Künstliche Intelligenz im Bau', 'Öffentliche Ausschreibungen', 'Aufmaß', 'Arbeitsschutz', 'Betriebsanweisungen', 'Gefährdungsbeurteilungen', 'Angebotskalkulation', 'Personalverwaltung'],
    'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': 'Digitale Mitarbeiter für Bau und Handwerk', 'itemListElement': [
        {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': BY_SLUG[s]['nav'], 'url': url(s)}} for s in LEISTUNGEN]},
}
WEBSITE = {'@type': 'WebSite', '@id': SITE + '/#website', 'url': SITE + '/', 'name': 'toolwerk', 'inLanguage': 'de-DE', 'publisher': {'@id': SITE + '/#org'}}


def faq_schema(pairs, page_url):
    return {'@type': 'FAQPage', '@id': page_url + '#fragen', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip(a)}} for q, a in pairs]}


def crumbs_schema(name, page_url):
    return {'@type': 'BreadcrumbList', '@id': page_url + '#brotkrumen', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Startseite', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': name, 'item': page_url}]}


# ------------------------------------------------------------------ Bausteine der Unterseiten
def sec(inner, soft=False, sid=''):
    return f'<section class="tw-sec{" tw-sec--soft" if soft else ""}"{f" id={chr(34)}{sid}{chr(34)}" if sid else ""}><div class="tw-wrap">{inner}</div></section>'


def heading(b, center=False):
    cls = ' tw-eyebrow--red' if b.get('type') == 'losses' else ''
    return f'<div class="tw-stack{" tw-center" if center else ""}" style="margin-bottom: 34px;"><p class="tw-eyebrow{cls}">{b["eyebrow"]}</p><h2 class="tw-h2">{b["h2"]}</h2></div>'


def block(b):
    t = b['type']
    soft = b.get('soft', False)
    if t == 'intro':
        parts = [heading(b), ''.join(f'<p class="tw-text">{p}</p>' for p in b['text'])]
        if b.get('cards'):
            parts.append('<div class="tw-grid tw-grid-3" style="margin-top: 40px;">' + ''.join(
                f'<div class="tw-card">{icon(i)}<h3 class="tw-h3">{h}</h3><p>{p}</p></div>' for i, h, p in b['cards']) + '</div>')
        if b.get('stats'):
            parts.append('<div class="tw-grid tw-grid-3" style="margin-top: 40px;">' + ''.join(
                f'<div class="tw-card"><div style="font-size: 40px; font-weight: 800; letter-spacing: -0.03em; color: #1c3d9b; line-height: 1;">{v}</div><p>{l}</p></div>' for v, l in b['stats']) + '</div>')
        return sec(''.join(parts), soft)
    if t == 'groups':
        cards = ''
        for i, h, items in b['groups']:
            li = ''.join(f'<li><a class="tw-link" href="{u}">{n} →</a></li>' if u else f'<li>{n}</li>' for n, u in items)
            cards += f'<div class="tw-card">{icon(i)}<h3 class="tw-h3">{h}</h3><ul class="tw-list" style="margin-top: 6px;">{li}</ul></div>'
        return sec(heading(b) + f'<div class="tw-grid tw-grid-2">{cards}</div><p class="tw-text" style="margin-top: 28px;">{b["after"]}</p>', soft)
    if t == 'table':
        def cell(v):
            return {'yes': '<span class="tw-yes">✓ Ja</span>', 'no': '<span class="tw-no">✕ Nein</span>'}.get(v, v)
        head_ = ''.join(f'<th scope="col">{h}</th>' for h in b['head'])
        rows = ''.join('<tr>' + ''.join(f'<td>{cell(c)}</td>' for c in r) + '</tr>' for r in b['rows'])
        return sec(heading(b) + f'<div class="tw-table-wrap"><table class="tw-table"><thead><tr>{head_}</tr></thead><tbody>{rows}</tbody></table></div><p class="tw-text" style="margin-top: 24px;">{b["after"]}</p>', soft)
    if t == 'panel':
        cards = ''.join(f'<div class="tw-card"><h3 class="tw-h3">{h}</h3><p>{p}</p></div>' for h, p in b['cards'])
        return f'<section class="tw-sec tw-sec--tight"><div class="tw-wrap"><div class="tw-panel"><div class="tw-stack" style="margin-bottom: 30px;"><p class="tw-eyebrow">{b["eyebrow"]}</p><h2 class="tw-h2">{b["h2"]}</h2><p class="tw-lead">{b["text"]}</p></div><div class="tw-grid tw-grid-3">{cards}</div><div class="tw-btns" style="margin-top: 30px;"><a class="tw-btn" href="/#check">Kennenlernen vereinbaren →</a></div></div></div></section>'
    if t == 'tags':
        tags = ''.join(f'<span>{x}</span>' for x in b['tags'])
        return sec(heading(b) + f'<p class="tw-text" style="margin: -14px 0 24px;">{b["text"]}</p><div class="tw-tags">{tags}</div>', soft)
    if t == 'cards':
        cards = ''.join(f'<div class="tw-card">{icon(i)}<h3 class="tw-h3">{h}</h3><p>{p}</p></div>' for i, h, p in b['cards'])
        return sec(heading(b) + f'<div class="tw-grid tw-grid-3">{cards}</div>', soft)
    if t == 'losses':
        items = ''.join(f'<div class="tw-loss">{icon(i)}<div><h3 class="tw-h3">{h}</h3><p>{p}</p></div></div>' for i, h, p in b['items'])
        return sec(heading(b) + f'<div class="tw-grid tw-grid-3">{items}</div>', soft)
    if t == 'steps':
        steps = ''.join(f'<li class="tw-step"><h3 class="tw-h3">{h}</h3><p>{p}</p></li>' for h, p in b['steps'])
        return sec(heading(b) + f'<ol class="tw-steps" style="margin: 0; padding: 0; list-style: none;">{steps}</ol>', soft)
    if t == 'split':
        li = ''.join(f'<li>{x}</li>' for x in b['list'])
        note = f'<p class="tw-text" style="margin-top: 22px; font-size: 15px; color: #4b566d;">{b["note"]}</p>' if b.get('note') else ''
        if b.get('aside'):
            h, p = b['aside']
            aside = f'<div class="tw-panel"><h3 class="tw-h3" style="font-size: 28px; letter-spacing: -0.03em; margin-bottom: 14px;">{h}</h3><p style="margin: 0; font-size: 17px; line-height: 1.65;">{p}</p></div>'
        else:
            h, items = b['aside_list']
            aside = f'<div class="tw-panel"><h3 class="tw-h3" style="font-size: 28px; letter-spacing: -0.03em; margin-bottom: 18px;">{h}</h3><ul class="tw-list">{"".join(f"<li>{x}</li>" for x in items)}</ul></div>'
        return sec(f'<div class="tw-split"><div>{heading(b)}<ul class="tw-list">{li}</ul>{note}</div>{aside}</div>', soft)
    if t == 'press':
        rows = ''
        for img, name, text, link in PRESS:
            inner = f'<img src="/assets/img/{img}.webp" alt="{name}" loading="lazy" decoding="async"><span>{name}<small>{text}</small></span>'
            rows += f'<a href="{link}" target="_blank" rel="noopener">{inner}</a>' if link else f'<div>{inner}</div>'
        return sec(heading(b) + f'<div class="tw-press">{rows}</div>', soft)
    raise ValueError(t)


def faq_html(pairs, name):
    det = ''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in pairs)
    return sec(f'<div class="tw-narrow" style="margin: 0 auto;"><div class="tw-stack tw-center" style="margin-bottom: 30px;"><p class="tw-eyebrow">Fragen</p><h2 class="tw-h2">Häufige Fragen {name}.</h2></div><div class="tw-faq">{det}</div></div>', sid='fragen')


def related_html(slugs):
    cards = ''.join(f'<a href="/{s}"><b>{BY_SLUG[s]["nav"]}</b><span>{TEASER[s]}</span><i>Ansehen →</i></a>' for s in slugs)
    return sec(f'<div class="tw-stack" style="margin-bottom: 26px;"><p class="tw-eyebrow">Weiterlesen</p><h2 class="tw-h2" style="font-size: clamp(26px, 3vw, 36px);">Mehr digitale Mitarbeiter.</h2></div><div class="tw-related">{cards}</div>', soft=True)


# ------------------------------------------------------------------ Startseite
def build_home(visuals_out, small):
    s = BeautifulSoup((SRC / 'home_body.html').read_text(), 'html.parser')

    # Logos tauschen, responsive Bilder
    for img in s.find_all('img'):
        if img.get('src', '').endswith('toolwerk-logo-rot.svg'):
            img['src'] = '/assets/img/toolwerk-logo.svg'
        stem = Path(img.get('src', '')).stem
        if stem in small:
            ss, w, h = srcset(stem, small[stem])
            img['srcset'] = ss
            img['sizes'] = {'hero-garkisch-leitungsgraben': '(max-width: 1132px) calc(100vw - 32px), 1100px',
                            'jonas-gruenberg-portraet': '(max-width: 560px) calc(100vw - 32px), 500px'}.get(stem, '(max-width: 760px) calc(100vw - 32px), 50vw')

    # Bausteine für Unterseiten mitnehmen (Fundkarte, QR-Beispiel)
    cap = s.find(string=lambda x: x and 'Ansicht aus dem Zuschlagsfinder' in x)
    fk = BeautifulSoup(str(cap.parent.parent), 'html.parser').div
    fk['style'] = 'position: relative; padding: 28px 8px 8px; min-width: 0;'
    visuals_out['fundkarte'] = str(fk)
    q = s.find(string=lambda x: x and 'Betriebsanweisung Minibagger' in x)
    qr = BeautifulSoup(str(q.parent.parent.parent.parent), 'html.parser').div
    qr['style'] = 'position: relative; min-height: 440px; border-radius: 28px; overflow: hidden; box-shadow: 0 40px 80px rgba(10,26,60,0.22);'
    visuals_out['qr'] = str(qr)

    # Navigation und Footer vereinheitlichen
    old_nav = s.find('nav').parent
    old_nav.replace_with(BeautifulSoup(nav(home=True), 'html.parser'))
    s.find('footer').replace_with(BeautifulSoup(footer(home=True), 'html.parser'))

    # H1 mit Kernbegriff: Eyebrow wandert in die H1
    h1 = s.find('h1')
    pill = h1.find_previous_sibling('span')
    if pill is not None:
        pill = pill.extract()
        pill['style'] = pill['style'] + ' line-height: 1.4; letter-spacing: normal;'
        big = s.new_tag('span', style='display: block;')
        for c in list(h1.contents):
            big.append(c.extract())
        h1.append(pill)
        h1.append(big)
        h1['style'] = h1['style'] + ' display: flex; flex-direction: column; align-items: center; gap: 22px;'

    # Produktkarten verlinken
    targets = {'Zuschlagsfinder': ('/zuschlagsfinder', 'Zuschlagsfinder ansehen →'), 'prüffähig': ('/pruefaehig', 'prüffähig ansehen →'),
               'Guard': ('/guard', 'Guard ansehen →'), 'Personalportal': ('/personalportal', 'Personalportal ansehen →')}
    for art in s.find(id='beispiele').find_all('article'):
        label = art.find('span', string=lambda x: x and x.strip() in targets)
        if label:
            href, text = targets[label.get_text(strip=True)]
            body = art.find_all('div', recursive=False)[-1]
            a = s.new_tag('a', href=href, attrs={'class': 'tw-link'}, style='margin-top: auto; font-size: 15px;')
            a.string = text
            body.append(a)
    tile = s.find(string=lambda x: x and x.strip() == 'Angebote kalkulieren')
    if tile:
        a = s.new_tag('a', href='/angebote-kalkulieren', style='color: inherit; text-decoration: none;')
        a.string = 'Angebote kalkulieren →'
        tile.replace_with(a)

    # Zuschlagsfinder- und Praxis-Abschnitt auf die Unterseiten verlinken
    zf_cta = s.find(id='zuschlagsfinder').find('a', attrs={'data-task': True})
    more = s.new_tag('a', href='/zuschlagsfinder', attrs={'class': 'tw-link'}, style='font-size: 16px;')
    more.string = 'Mehr zum Zuschlagsfinder →'
    zf_cta.insert_after(more)
    pr_a = s.find(id='praxis').find('a', string=lambda x: x and 'Das will ich auch' in x)
    if pr_a:
        wrap = s.new_tag('div', style='display: flex; flex-wrap: wrap; align-items: center; gap: 14px 24px;')
        pr_a.wrap(wrap)
        g = s.new_tag('a', href='/guard', attrs={'class': 'tw-link'}, style='font-size: 16px;')
        g.string = 'Mehr zu Guard →'
        wrap.append(g)
    wer = s.find(string=lambda x: x and 'fangen mit der Aufgabe an, die wirklich liegen bleibt' in x)
    if wer:
        a = s.new_tag('a', href='/ueber-uns', attrs={'class': 'tw-link'}, style='font-size: 16px;')
        a.string = 'Mehr über uns →'
        wer.parent.insert_after(a)

    faqs = [(d.summary.contents[0].strip(), d.p.get_text(strip=True)) for d in s.find(id='fragen').find_all('details')]
    page_url = SITE + '/'
    ld = {'@context': 'https://schema.org', '@graph': [ORG, WEBSITE,
          {'@type': 'WebPage', '@id': page_url + '#seite', 'url': page_url, 'name': 'Digitale Mitarbeiter für Bau und Handwerk | toolwerk',
           'isPartOf': {'@id': SITE + '/#website'}, 'about': {'@id': SITE + '/#org'}, 'inLanguage': 'de-DE',
           'primaryImageOfPage': SITE + '/assets/img/hero-garkisch-leitungsgraben.webp'},
          faq_schema(faqs, page_url)]}
    ss, _, _ = srcset('hero-garkisch-leitungsgraben', small['hero-garkisch-leitungsgraben'])
    pre = f'<link rel="preload" as="image" href="/assets/img/hero-garkisch-leitungsgraben.webp" imagesrcset="{ss}" imagesizes="(max-width: 1132px) calc(100vw - 32px), 1100px" fetchpriority="high">\n'
    title = 'Digitale Mitarbeiter für Bau und Handwerk | toolwerk'
    desc = 'Wir übernehmen die Arbeit, die im Büro liegen bleibt: Ausschreibungen, Aufmaß, Angebote, Unterlagen. Digitale Mitarbeiter mit KI, Ihr Team gibt frei.'
    page = head(title, desc, '/', '/og.jpg', ld, extra=pre) + f'<body style="margin:0">\n{s}\n<script src="/assets/js/site.js" defer></script>\n</body>\n</html>\n'
    (OUT / 'index.html').write_text(page)
    return title


# ------------------------------------------------------------------ Unterseite
def build_page(p, visuals, small):
    slug, page_url = p['slug'], url(p['slug'])
    task = p.get('task', '')
    if p.get('visual'):
        right = visuals[p['visual']].replace('loading="lazy"', 'fetchpriority="high"')
        primary = None
    else:
        stem, alt, pos = p['image'][:3]
        ratio = p['image'][3] if len(p['image']) > 3 else '4 / 3'
        ss, w, h = srcset(stem, small[stem])
        right = (f'<div class="tw-frame"><img class="tw-photo" src="/assets/img/{stem}.webp" srcset="{ss}" sizes="(max-width: 980px) calc(100vw - 32px), 540px" '
                 f'width="{w}" height="{h}" alt="{html.escape(alt)}" fetchpriority="high" decoding="async" style="aspect-ratio: {ratio}; object-position: {pos};"></div>')
        primary = f'{SITE}/assets/img/{stem}.webp'
    hero = f"""<section class="tw-hero"><div class="tw-wrap"><div class="tw-hero-grid">
<div class="tw-stack">
<nav aria-label="Brotkrumen"><ol class="tw-crumbs"><li><a href="/">Startseite</a></li><li aria-current="page">{p['nav']}</li></ol></nav>
<span class="tw-chip">{p['chip']}</span>
<h1 class="tw-h1{' tw-h1--s' if p.get('h1_small') else ''}">{p['h1']}</h1>
<p class="tw-lead">{p['lead']}</p>
<div class="tw-btns"><a class="tw-btn" href="{cta_href(task)}">{CAL_CTA}</a>{'<a class="tw-link" href="#fragen">Häufige Fragen</a>' if p['faq'] else ''}</div>
</div>
<div>{right}</div>
</div></div></section>"""
    main = hero + ''.join(block(b) for b in p['blocks'])
    if p['faq']:
        main += faq_html(p['faq'], p.get('faq_name', 'zu ' + p['nav']))
    main += cta_panel(task) + related_html(p['related'])

    graph = [ORG, WEBSITE, crumbs_schema(p['nav'], page_url)]
    webpage = {'@type': 'AboutPage' if p.get('about') else 'WebPage', '@id': page_url + '#seite', 'url': page_url, 'name': p['title'],
               'description': p['description'], 'isPartOf': {'@id': SITE + '/#website'}, 'breadcrumb': {'@id': page_url + '#brotkrumen'},
               'inLanguage': 'de-DE', 'dateModified': TODAY}
    if primary:
        webpage['primaryImageOfPage'] = primary
    if p.get('service'):
        name, stype = p['service']
        graph.append({'@type': 'Service', '@id': page_url + '#leistung', 'name': name, 'serviceType': stype, 'description': p['description'],
                      'provider': {'@id': SITE + '/#org'}, 'areaServed': {'@type': 'Country', 'name': 'Deutschland'},
                      'audience': {'@type': 'BusinessAudience', 'name': 'Betriebe aus Bau und Handwerk'}, 'url': page_url})
        webpage['mainEntity'] = {'@id': page_url + '#leistung'}
    if p.get('about'):
        subject = [{'@type': 'NewsArticle', 'url': l, 'publisher': {'@type': 'Organization', 'name': n}} for _, n, _, l in PRESS if l and 'podigee' not in l and 'nordkurier' not in l]
        subject.append({'@type': 'PodcastEpisode', 'url': PRESS[3][3], 'partOfSeries': {'@type': 'PodcastSeries', 'name': 'Mitternachtstalk'}})
        person = {'@type': 'Person', '@id': SITE + '/ueber-uns#jonas', 'name': 'Jonas Grünberg', 'jobTitle': 'Gründer und Geschäftsführer',
                  'worksFor': {'@id': SITE + '/#org'}, 'image': SITE + '/assets/img/jonas-gruenberg-portraet.webp', 'url': page_url,
                  'homeLocation': {'@type': 'Place', 'name': 'Prignitz, Brandenburg'}, 'subjectOf': subject}
        graph.append(person)
        webpage['mainEntity'] = {'@id': SITE + '/ueber-uns#jonas'}
    graph.append(webpage)
    if p['faq']:
        graph.append(faq_schema(p['faq'], page_url))
    og = f'/og/{slug}.jpg'
    page = head(p['title'], p['description'], '/' + slug, og, {'@context': 'https://schema.org', '@graph': graph}) + \
        f'<body>\n{nav(current=slug)}\n<main>\n{main}\n</main>\n{footer()}\n</body>\n</html>\n'
    (OUT / f'{slug}.html').write_text(page)


def build_legal(slug, title):
    content = (SRC / 'legal' / f'{slug}.html').read_text()
    ld = {'@context': 'https://schema.org', '@graph': [ORG, WEBSITE, {'@type': 'WebPage', 'url': url(slug), 'name': title, 'isPartOf': {'@id': SITE + '/#website'}, 'inLanguage': 'de-DE'}]}
    page = head(f'{title} | toolwerk', f'{title} der Grünberg Solutions GmbH für die Marke toolwerk.', '/' + slug, '/og.jpg', ld, robots='noindex, follow') + \
        f'<body>\n{nav()}\n<main class="tw-legal">{content}</main>\n{footer()}\n</body>\n</html>\n'
    (OUT / f'{slug}.html').write_text(page)


def build_404():
    links = ''.join(f'<a href="/{s}"><b>{BY_SLUG[s]["nav"]}</b><span>{TEASER[s]}</span><i>Ansehen →</i></a>' for s in LEISTUNGEN[:3])
    page = head('Seite nicht gefunden | toolwerk', 'Diese Seite gibt es nicht. Zur Startseite von toolwerk.', '/404', '/og.jpg',
                {'@context': 'https://schema.org', '@graph': [ORG, WEBSITE]}, robots='noindex, follow') + \
        f"""<body>
{nav()}
<main><section class="tw-hero"><div class="tw-wrap tw-stack tw-center" style="text-align: center;">
<p class="tw-eyebrow">Fehler 404</p><h1 class="tw-h1">Diese Seite gibt es nicht.</h1>
<p class="tw-lead">Aber die Arbeit, die bei Ihnen liegen bleibt, gibt es bestimmt.</p>
<div class="tw-btns"><a class="tw-btn" href="/">Zur Startseite</a></div>
</div></section>
<section class="tw-sec tw-sec--tight"><div class="tw-wrap"><div class="tw-related">{links}</div></div></section></main>
{footer()}
</body>
</html>
"""
    (OUT / '404.html').write_text(page)


# ------------------------------------------------------------------ Vorschaubilder, Logos
def og_images(home_title):
    from playwright.sync_api import sync_playwright
    import base64
    logo = 'data:image/svg+xml;base64,' + base64.b64encode((IMG / 'toolwerk-logo.svg').read_bytes()).decode()
    font = (OUT / 'assets' / 'fonts' / 'plus-jakarta-sans-latin.woff2').as_uri()
    (OUT / 'og').mkdir(exist_ok=True)
    jobs = [('og.jpg', 'Digitale Mitarbeiter für Bau und Handwerk', 'Was im Büro liegen bleibt, kostet Sie <span>jeden Monat Geld.</span>', 'hero-garkisch-leitungsgraben')]
    for p in PAGES:
        photo = p.get('og_image') or (p['image'][0] if p.get('image') else 'garkisch-team-hof')
        h = re.sub(r'<span class="tw-blue">(.*?)</span>', r'<span>\1</span>', p['h1'])
        jobs.append((f'og/{p["slug"]}.jpg', p['chip'], h, photo))
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--allow-file-access-from-files'])
        pg = b.new_page(viewport={'width': 1200, 'height': 630})
        for out, chip, h, photo in jobs:
            fs = 58 if len(strip(h)) < 70 else 46
            photo_uri = (IMG / f'{photo}.webp').as_uri()
            pg.set_content(f"""<html><head><style>@font-face{{font-family:J;src:url({font}) format("woff2");font-weight:200 800}}
body{{margin:0;width:1200px;height:630px;font-family:J,sans-serif;background:radial-gradient(70% 90% at 20% 0%,#e3eaf8 0%,#fff 70%);position:relative;overflow:hidden;color:#0b1428}}
.p{{position:absolute;right:0;top:0;width:430px;height:630px;background:url({photo_uri}) center/cover;filter:saturate(.92) contrast(1.04)}}
.w{{position:absolute;left:64px;top:60px;width:640px}}
.c{{display:inline-flex;align-items:center;gap:10px;margin-top:46px;padding:8px 18px 8px 14px;border-radius:999px;background:#fff;border:1px solid #d5ddee;font-size:20px;font-weight:700;color:#1c3d9b}}
.c:before{{content:"";width:10px;height:10px;border-radius:50%;background:#c5301f}}
h1{{margin:26px 0 0;font-size:{fs}px;line-height:1.04;font-weight:800;letter-spacing:-.04em}} h1 span{{color:#1c3d9b}}</style></head>
<body><div class="p"></div><div class="w"><img src="{logo}" style="height:40px"><br><span class="c">{chip}</span><h1>{h}</h1></div></body></html>""".replace('<span>jeden Monat Geld.</span>', '<span style="color:#c5301f">jeden Monat Geld.</span>'))
            pg.wait_for_timeout(250)
            tmp = OUT / '_og.png'
            pg.screenshot(path=str(tmp))
            Image.open(tmp).convert('RGB').save(OUT / out, 'JPEG', quality=84, optimize=True, progressive=True)
            tmp.unlink()
        # quadratisches Logo für Google (Organization.logo)
        pg = b.new_page(viewport={'width': 512, 'height': 512})
        pg.set_content(f'<body style="margin:0;width:512px;height:512px;background:#fff;display:grid;place-items:center"><img src="{logo}" style="width:420px"></body>')
        pg.wait_for_timeout(200)
        pg.screenshot(path=str(IMG / 'toolwerk-logo-quadrat.png'))
        b.close()


# ------------------------------------------------------------------ Hauptablauf
def main():
    shutil.copy(SRC / 'site.js', OUT / 'assets' / 'js' / 'site.js')
    small = responsive_images()
    visuals = {}
    css = (SRC / 'base.css').read_text() + '\n' + (SRC / 'pages.css').read_text()
    (OUT / 'assets' / 'css' / 'site.css').write_text(css)
    home_title = build_home(visuals, small)
    for p in PAGES:
        build_page(p, visuals, small)
    build_legal('impressum', 'Impressum')
    build_legal('datenschutz', 'Datenschutzerklärung')
    build_404()
    og_images(home_title)

    # Manifest, Sitemap, robots, llms.txt
    (OUT / 'site.webmanifest').write_text(json.dumps({
        'name': 'toolwerk', 'short_name': 'toolwerk', 'start_url': '/', 'display': 'browser', 'background_color': '#ffffff', 'theme_color': '#ffffff',
        'icons': [{'src': '/apple-touch-icon.png', 'sizes': '180x180', 'type': 'image/png'}, {'src': '/favicon.svg', 'sizes': 'any', 'type': 'image/svg+xml'}]}, indent=1))
    prio = {'digitale-mitarbeiter': '0.9', 'zuschlagsfinder': '0.9', 'ueber-uns': '0.6'}
    urls = [(SITE + '/', '1.0', 'og.jpg', 'hero-garkisch-leitungsgraben')] + [(url(p['slug']), prio.get(p['slug'], '0.8'), f'og/{p["slug"]}.jpg', None) for p in PAGES]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    for u, pr, og, _ in urls:
        sm += f'<url><loc>{u}</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq><priority>{pr}</priority><image:image><image:loc>{SITE}/{og}</image:loc></image:image></url>\n'
    (OUT / 'sitemap.xml').write_text(sm + '</urlset>\n')
    (OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    llms = ['# toolwerk', '', '> Digitale Mitarbeiter für Bau und Handwerk. Ein digitaler Mitarbeiter ist KI, die eine feste Aufgabe im Betrieb übernimmt, mit den Unterlagen des Betriebs arbeitet und alles zur Freigabe vorlegt. toolwerk ist eine Marke der Grünberg Solutions GmbH aus Perleberg (Brandenburg).', '',
            '## Seiten', f'- [Startseite]({SITE}/): Überblick, Beispiele, Ablauf-Check und Terminvereinbarung']
    llms += [f'- [{p["nav"]}]({url(p["slug"])}): {strip(p["description"])}' for p in PAGES]
    llms += ['', '## Kontakt', '- Grünberg Solutions GmbH, Großer Markt 16, 19348 Perleberg', '- Telefon +49 152 55604258, kontakt@gruenbergsolutions.de', f'- Erstgespräch: {SITE}/#check', '']
    (OUT / 'llms.txt').write_text('\n'.join(llms))
    for old in ['og.png', 'assets/img/toolwerk-logo-rot.svg']:
        if (OUT / old).exists():
            (OUT / old).unlink()

    # Cache-Busting
    for asset in ('assets/css/site.css', 'assets/js/site.js'):
        h = hashlib.sha1((OUT / asset).read_bytes()).hexdigest()[:10]
        for f in OUT.glob('*.html'):
            t = re.sub(r'/' + re.escape(asset) + r'(\?v=[0-9a-f]+)?"', '/' + asset + '?v=' + h + '"', f.read_text())
            f.write_text(t)
    files = sorted(str(x.relative_to(OUT)) for x in OUT.rglob('*') if x.is_file() and x.name != 'site-manifest.json')
    (OUT / 'site-manifest.json').write_text(json.dumps({'files': files}, indent=1))
    print('fertig:', len(files), 'Dateien,', round(sum((OUT / f).stat().st_size for f in files) / 1024), 'KB')


if __name__ == '__main__':
    main()
