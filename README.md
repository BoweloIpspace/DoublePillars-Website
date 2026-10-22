# DoublePillars website

Static HTML site. Work for the complete company profile is on `feat/combined-site-profile`; do not merge into `main` or deploy without a separate instruction.

## Test locally (Windows)

From your existing checkout, first commit or stash any local edits, then run:

```powershell
git fetch origin
git switch feat/combined-site-profile
git pull --ff-only origin feat/combined-site-profile
py -m http.server 5500
```

If you need a fresh checkout:

```powershell
git clone --branch feat/combined-site-profile https://github.com/BoweloIpspace/DoublePillars-Website.git
cd DoublePillars-Website
py -m http.server 5500
```

Open <http://localhost:5500>. Use Ctrl+C to stop the server. On macOS/Linux use `python3` instead of `py`.

Check the Services dropdown, scrolling service cards, every full service page, Company Profile, footer links, and browser Back/Forward. Resize the browser or use its mobile device tools to check the mobile menus and text wrapping. Existing hash URLs such as `index.html#taxation` retain the full corresponding service information.

The site uses external font, Tailwind and icon CDNs and some external photographs, so an internet connection is needed for the existing complete visual styling. Contact form delivery requires the site's existing hosting form handler; a local Python static server does not send enquiries. Verification does not submit the form or contact clients.

## Content and navigation verification

```powershell
py scripts/verify_site.py
```

This checks all 22 PDF pages and 258 transcribed blocks against their actual HTML destinations, every local link and fragment, local image/script/CSS resources, duplicate IDs, and redundant return controls. No third-party Python packages are required.

The original attached PDF is preserved byte-for-byte at `assets/company-profile-2021.pdf`. `docs/profile-source.json` contains the page-to-HTML mapping and exact transcribed blocks; readable page transcriptions are in `docs/profile-source/`. Line wrapping and bullet presentation are adapted to HTML. Source spelling, grammar, capitalization, historical statements and numbers are retained. The training cycle from page 14 is included both as its original graphic and as readable text. No PDF text is loaded asynchronously: it is directly in the HTML.

| PDF pages | Website destination |
| --- | --- |
| 1–5, 19–22 | `company-profile.html` |
| 6, 8 | `forensic-services.html` |
| 7 | `index.html#services` |
| 9 | `accounting-management.html` |
| 10–12 | `tax-advisory-compliance.html` |
| 13 | `corporate-advisory.html` |
| 14 | `training.html` |
| 15–16 | `corporate-finance.html` |
| 17 | `corporate-secretarial.html` |
| 18 | `payroll-services.html` |

The existing navy/red design, original image files, and small footer text links are preserved. Service navigation opens the full service pages, and retained service hash routes also display the full text. The original source PDF is available through a small footer text link on each standalone page.

## Verification performed

- Content and link checker: all 22 PDF pages, 258 exact text blocks, 10 HTML pages and 274 links passed.
- Browser checks in Chromium: all HTML pages at 360, 768 and 1440 pixels; mobile menu and standalone service dropdown; full service navigation; tax-planning anchor; browser Back/Forward; all 18 primary and legacy routes. No JavaScript errors, broken images or horizontal overflow were found.
- Existing image assets and image URLs were compared against the previous commit. The home page footer markup is unchanged.
- The original PDF's SHA-256 checksum matches the attachment: `007b4587460b463deb73e2b99e913e683bac8d2dc0bcd91ff219203019ef733e`.
- No production deployment or contact-form submission was performed.
