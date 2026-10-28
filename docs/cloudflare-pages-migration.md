# Cloudflare Pages migration preparation

This repository is prepared for a Cloudflare Pages Direct Upload migration without changing the existing Netlify publish directory or provisioning Cloudflare resources.

## Current audit

- The site is static HTML: nine pages plus the existing `dist` output.
- `netlify.toml` only sets Netlify's publish directory to `dist`; it has no redirects, functions, build command, or environment variables.
- `_headers` is valid Pages-compatible static header syntax and can remain in the output. Cloudflare Pages parses `_headers` from the static output; it is not served as an asset.
- There is no `_redirects` file and no Netlify function.
- The current form is Netlify-specific (`data-netlify`, `netlify-honeypot`, `form-name`) and currently posts to `/`. It is intentionally unchanged in the existing source and `dist`.
- The local `.netlify` directory contains ignored CLI metadata only; it is not part of the deployment.

## Cloudflare staging output

The existing `dist` directory is already a clean static output. To create an isolated Cloudflare candidate:

```powershell
.\scripts\prepare-cloudflare-pages.ps1 -Clean
py scripts\verify-cloudflare-pages.py --root .cloudflare-pages
```

The script copies `dist` to `.cloudflare-pages`, then changes only the staging copy's form transport to `POST /api/contact`. It also writes `_routes.json` with only `/api/contact` included, adds `noindex` headers for `*.pages.dev` hostnames, and leaves `dist` unchanged. Do not deploy the staging copy to production until the canonical-domain decision below is approved.

For the recommended Cloudflare URL strategy, pass the approved production origin together with `-UseExtensionlessUrls`:

```powershell
# Replace the placeholder with the approved official HTTPS origin before running.
.\scripts\prepare-cloudflare-pages.ps1 -Clean -CanonicalBaseUrl https://<APPROVED_OFFICIAL_ORIGIN> -UseExtensionlessUrls
```

This replaces the temporary `https://doublepillars.netlify.app` base, changes staged internal links and SEO URLs to extensionless paths, updates the sitemap, and writes explicit 301 redirects from the existing `.html` URLs. No replacement is made by default so the approved SEO metadata remains intact until the domain is approved.

## Deployment commands (not run here)

The current repository has no package manifest or build step. Direct Upload is therefore the appropriate Cloudflare Pages mode for the prebuilt output. Wrangler must be installed or available through `npx` by the person authorized to deploy.

Candidate deployment with the contact Function, after creating the Pages project and configuring its preview variables/binding:

```powershell
npx wrangler pages deploy .cloudflare-pages --project-name=<CLOUDFLARE_PAGES_PROJECT>
```

Run those commands from the repository root. Wrangler detects the root `functions` directory when it deploys the Pages project. Dashboard drag-and-drop is not suitable for the Function candidate because Cloudflare documents that drag-and-drop does not compile a `functions` directory. The unchanged `dist` output is intentionally retained for Netlify and should not be used for the contact cutover.

The Function fails closed when its KV binding or email variables/secrets are absent, so no email is sent in the current unconfigured state. Do not submit the preview form until the provider, sender, recipient, origin allow-list, KV binding, and secrets have been configured and approved.

For a preview deployment, add a branch name:

```powershell
npx wrangler pages deploy .cloudflare-pages --project-name=<CLOUDFLARE_PAGES_PROJECT> --branch=migration-preview
```

## Netlify replacements

| Netlify item | Cloudflare Pages preparation |
| --- | --- |
| `netlify.toml` `[build] publish = "dist"` | No static Pages config file is required for Direct Upload; the existing `dist` directory is the source for the isolated Cloudflare candidate. |
| `_headers` | Keep `_headers` in the static output. It applies to static responses. Function responses set their own headers in `functions/api/contact.js`. |
| Netlify Forms POST to `/` | Staged form posts to `/api/contact`, handled by the Pages Function. The live Netlify source and `dist` remain unchanged. |
| Netlify form storage/notifications | No automatic Cloudflare email is assumed. The Function calls the selected email provider's API. |
| Netlify redirects | None found. Add a Cloudflare `_redirects` file only if approved redirect rules are later required. |
| Netlify local state `.netlify` | Remains ignored and is excluded from the candidate output. |

## Secure contact delivery plan

`functions/api/contact.js` is a provider-backed candidate, not an email service by itself. It:

- accepts only POST requests from an allow-listed origin;
- accepts only the URL-encoded payload used by the staged browser form;
- validates and length-limits every field, ignores the Netlify-only `form-name`, and uses a honeypot;
- requires a Cloudflare KV binding for a per-IP rate limit and fails closed if it is missing;
- sends through the Resend HTTPS API using a server-side API key, with the visitor's email as `reply_to`;
- never exposes provider credentials or provider error bodies to the browser; and
- returns `Cache-Control: no-store` plus security headers because Pages `_headers` do not apply to Function responses.

Before enabling it in production, an account owner must choose and approve the email provider, verify the sender domain with that provider, create/bind the rate-limit KV namespace, and add the required production and preview variables/secrets in Cloudflare Pages:

| Name | Type | Purpose |
| --- | --- | --- |
| `ALLOWED_ORIGINS` | variable | Comma-separated exact HTTPS origin(s) for production and preview. |
| `CONTACT_TO_EMAIL` | variable | Set to `doublepillars@gmail.com` in Preview and Production. |
| `CONTACT_FROM_EMAIL` | variable | Leave unchanged until a verified sending domain is available. |
| `CONTACT_RATE_LIMIT_MAX` | variable | Optional per-IP window limit; defaults to 5. |
| `CONTACT_RATE_LIMIT_WINDOW_SECONDS` | variable | Optional window; defaults to 900 seconds. |
| `RESEND_API_KEY` | encrypted secret | Sending-only provider key. |
| `CONTACT_RATE_LIMIT` | KV binding | KV namespace used for rate limiting. |

The form integration is intentionally staged rather than applied to the live Netlify source. After a preview test, the owner must approve the cutover, verify a real test enquiry, and then decide whether to merge the staged form transport into the source branch.

The nine source pages already contain `doublepillars@gmail.com` in their contact information and structured data. No unrelated email addresses were changed, and the Resend API key is not stored in this repository.

## SEO and URL decision required

The current nine-page SEO URLs use `.html` and the temporary `doublepillars.netlify.app` origin. Cloudflare Pages redirects HTML pages such as `/contact.html` to `/contact`. The prepared safe strategy is:

1. Use the `-UseExtensionlessUrls` staging mode to make extensionless URLs canonical.
2. Keep explicit 301 rules for all existing `.html` page URLs, preserving old bookmarks and inbound links.
3. Keep `pages.dev` previews `noindex`, and submit only the approved custom-origin sitemap after the cutover.

This mode is opt-in because it changes URL metadata in the staging copy. The source files and existing Netlify `dist` remain unchanged.

The current SEO audit finds one consistent temporary origin across all nine canonicals, Open Graph URLs, JSON-LD page URLs, `sitemap.xml`, and `robots.txt`. The temporary Netlify origin is retained until the official domain is approved; no Cloudflare preview address is promoted to a permanent business URL. The extensionless staging mode is the future-domain path, and its `pages.dev` noindex headers remain enabled.

## Netlify retirement preparation

Retirement is intentionally not performed in this repository. Keep both Netlify projects and the current Netlify deployment available as rollback options until all of the following are complete:

1. Approve the official domain and canonical URL style.
2. Configure Cloudflare Pages Preview and Production variables, KV binding, email provider, sender domain, and `CONTACT_TO_EMAIL=doublepillars@gmail.com`.
3. Test the Cloudflare preview without submitting a real customer enquiry, then perform one separately approved controlled enquiry test.
4. Configure the custom domain and DNS cutover, verify HTTPS, redirects, headers, sitemap, robots, all nine pages, assets and the Function response.
5. Monitor the new deployment and preserve the Netlify rollback path for an agreed observation period.
6. Only after approval, export any required Netlify form records, disable Netlify build hooks, remove obsolete DNS references, and delete Netlify projects last.

No Netlify project, DNS record, rollback option, or form history was deleted.

## Required account access/approval

- Cloudflare account access to create/select the Pages project, set production/preview variables and secrets, bind KV, and configure the approved custom domain/DNS.
- An approved canonical production origin and redirect/URL policy.
- An approved email provider, verified sender domain, receiving mailbox, sending-only API key, and provider retention/privacy decision.
- Authorization for a non-production preview test, including one controlled test enquiry. No resource creation, login, deployment, DNS change, email send, or form submission was performed here.
