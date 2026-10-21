# tool-werk.de

Statische Webseite von toolwerk (Marke der Grünberg Solutions GmbH). Alles, was live geht, liegt in `site/`.

## Aufbau

| Pfad | Was |
|---|---|
| `src/build.py` | Baut `site/` komplett: Startseite, Unterseiten, Rechtstexte, 404, Sitemap, robots.txt, llms.txt, Vorschaubilder, strukturierte Daten |
| `src/home_body.html` | Startseite aus dem Design-Canvas (Version 6), wird beim Bau mit Navigation, Footer, Verlinkung und SEO ergänzt |
| `src/content.py` | Texte und Aufbau aller Unterseiten |
| `src/legal/` | Impressum und Datenschutz (Text 1:1) |
| `src/base.css`, `src/pages.css` | Stile, werden zu `site/assets/css/site.css` |
| `src/site.js` | Ablauf-Check mit Calendly, Vorauswahl über `/?aufgabe=...#check` |
| `vercel.json` | saubere URLs, Weiterleitungen (`/aim`, angebote-in-minuten.de), Caching |

Bauen: `python3 src/build.py` (braucht beautifulsoup4, pillow, playwright mit Chromium).

## Regeln für Texte

Sie-Form, kurze Sätze, keine Gedankenstriche, keine erfundenen Zahlen, keine Leistungs- oder Zeitversprechen, nie „rechtssicher“. Kunden nur mit Freigabe namentlich. Immer „toolwerk“, nie „toolwerk by grünberg“.

## Hosting

Vercel-Projekt `toolwerk-website`, Domains tool-werk.de und angebote-in-minuten.de (leitet auf `/angebote-kalkulieren`).
