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

Check the Services dropdown, scrolling service cards, every full service page, profile sections, footer links, and browser Back/Forward. Resize the browser or use its mobile device tools to check the mobile menus and text wrapping. Existing hash URLs such as `index.html#taxation` retain the full corresponding service information.

The site uses external font, Tailwind and icon CDNs and some external photographs, so an internet connection is needed for the existing complete visual styling. Contact form delivery requires the site's existing hosting form handler; a local Python static server does not send enquiries. Verification does not submit the form or contact clients.

## Content and navigation verification

```powershell
py scripts/verify_site.py
```

This checks all 22 PDF pages and 258 transcribed blocks against their mapped HTML destinations, every local link and fragment, local image/script/CSS resources, duplicate IDs, and redundant return controls. Some profile mappings are intentionally source-only because the current site has nine HTML pages and no standalone company profile page. No third-party Python packages are required.

The original attached PDF is preserved byte-for-byte at `assets/company-profile-2021.pdf`. `docs/profile-source.json` contains the page-to-HTML mapping and exact transcribed blocks; readable page transcriptions are in `docs/profile-source/`. Line wrapping and bullet presentation are adapted to HTML. Source spelling, grammar, capitalization, historical statements and numbers are retained. The training cycle from page 14 is included both as its original graphic and as readable text. No PDF text is loaded asynchronously: it is directly in the HTML.

| PDF pages | Website destination |
| --- | --- |
| 1-5, 19-22 | Source-only mapping retained in `docs/profile-source.json` |
| 6, 8 | `forensic-services.html` |
| 7 | `index.html#services` |
| 9 | `accounting-management.html` |
| 10–12 | `tax-advisory-compliance.html` |
| 13 | `corporate-advisory.html` |
| 14 | `training.html` |
| 15–16 | `corporate-finance.html` |
| 17 | `corporate-secretarial.html` |
| 18 | `payroll-services.html` |

The existing navy/red design, original image files, and small footer text links are preserved. Service navigation opens the full service pages, and retained service hash routes also display the full text. The original source PDF remains in `assets/company-profile-2021.pdf` for project reference.

## SEO

The official non-www canonical base is `https://doublepillarsconsultants.com`. Cloudflare production publishes extensionless canonical URLs for all nine pages and permanently redirects the legacy `.html` URLs. The `www` hostname is redirected to the non-www hostname by the Cloudflare Pages middleware.

## Netlify deployment preparation

`netlify.toml` points Netlify at the curated `dist` directory. When deployment is authorised, prepare it with:

```powershell
.\scripts\prepare-netlify-publish.ps1
```

The script copies only the nine HTML pages, required assets, `sitemap.xml`, `robots.txt`, and `_headers`. It excludes the PDF, documentation, Git metadata, verification scripts, and other development files. It is not run by local verification.

## Cloudflare Pages deployment

See [`docs/cloudflare-pages-migration.md`](docs/cloudflare-pages-migration.md) for the Cloudflare staging script, deployment commands, Pages Function contact-delivery plan, redirect behavior, required account configuration, and Resend sender-verification steps. The migration script creates an isolated `.cloudflare-pages` candidate from `dist`; it does not modify the source publish directory while preparing the Cloudflare candidate.

The approved business recipient is `doublepillars@gmail.com`. Configure `ALLOWED_ORIGINS` as `https://doublepillarsconsultants.com,https://www.doublepillarsconsultants.com` and `CONTACT_TO_EMAIL=doublepillars@gmail.com` in Cloudflare Pages. Keep `CONTACT_FROM_EMAIL` unchanged until `doublepillarsconsultants.com` is verified in Resend. Never commit or replace `RESEND_API_KEY`.

Prepare and verify the deployment candidate with:

```powershell
.\scripts\prepare-netlify-publish.ps1 -Clean
.\scripts\prepare-cloudflare-pages.ps1 -Clean
py scripts\verify-seo.py --root dist
py scripts\verify-cloudflare-pages.py --root .cloudflare-pages
```

## Verification performed

- Static audit: 9 HTML pages, local links/fragments, local assets, duplicate IDs, image alt text, form labels, and 17 local HTTP resources passed.
- The existing profile verifier reports 22 known transcription mismatches in Tax Advisory and Corporate Secretarial content that reflect approved client wording revisions; it introduces no local-link or asset failures.
- Browser checks were not performed in this environment because no controlled browser was available; no responsive-rendering claim is made here.
- Existing image assets and image URLs were compared against the previous commit. The home page footer markup is unchanged.
- The original PDF's SHA-256 checksum matches the attachment: `007b4587460b463deb73e2b99e913e683bac8d2dc0bcd91ff219203019ef733e`.
- No contact-form submission was performed; deployment status is reported in the task handoff.
