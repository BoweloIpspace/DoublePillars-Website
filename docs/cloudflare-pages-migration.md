# Cloudflare Pages production preparation

This repository is prepared for a Cloudflare Pages Direct Upload deployment without changing Netlify settings or provisioning Cloudflare resources.

## Current audit

- The site is static HTML: nine pages plus the existing `dist` output.
- `netlify.toml` only sets Netlify's publish directory to `dist`; it has no redirects, functions, build command, or environment variables.
- `_headers` is valid Pages-compatible static header syntax and can remain in the output. Cloudflare Pages parses `_headers` from the static output; it is not served as an asset.
- The source repository has no `_redirects` file; the Cloudflare staging script generates one for legacy `.html` URLs. The Pages Function is under `functions/` and is not a Netlify Function.
- The source form remains compatible with the existing Netlify publish path. The Cloudflare staging copy removes Netlify transport markers and posts to `/api/contact`.
- The local `.netlify` directory contains ignored CLI metadata only; it is not part of the deployment.

## Cloudflare staging output

The existing `dist` directory is a clean static output. To create an isolated Cloudflare candidate with the official domain and extensionless URLs:

```powershell
.\scripts\prepare-netlify-publish.ps1 -Clean
.\scripts\prepare-cloudflare-pages.ps1 -Clean
py scripts\verify-cloudflare-pages.py --root .cloudflare-pages
```

The script copies `dist` to `.cloudflare-pages`, changes only the staging copy's form transport to `POST /api/contact`, enables the official non-www canonical origin, changes internal links and SEO URLs to extensionless paths, writes legacy `.html` 301 redirects, invokes the Pages middleware on every route, adds `noindex` headers for `*.pages.dev` hostnames, and leaves `dist` unchanged.

The official origin and extensionless mode are now the script defaults. An explicit equivalent invocation is:

```powershell
 .\scripts\prepare-cloudflare-pages.ps1 -Clean -CanonicalBaseUrl https://doublepillarsconsultants.com -UseExtensionlessUrls
```

This keeps `https://doublepillarsconsultants.com` as the canonical non-www origin, changes staged internal links and SEO URLs to extensionless paths, updates the sitemap, and writes explicit 301 redirects from the existing `.html` URLs. The Pages middleware also enforces these legacy redirects when Functions are invoked.

## Deployment command

The current repository has no package manifest or build step. Direct Upload is therefore the appropriate Cloudflare Pages mode for the prebuilt output. Wrangler must be installed or available through `npx` by the person authorized to deploy.

Production deployment with the contact Function, after selecting the existing Pages project and configuring its variables/binding:

```powershell
npx wrangler pages deploy .cloudflare-pages --project-name=<CLOUDFLARE_PAGES_PROJECT>
```

Run those commands from the repository root. Wrangler detects the root `functions` directory when it deploys the Pages project. Dashboard drag-and-drop is not suitable for the Function candidate because Cloudflare documents that drag-and-drop does not compile a `functions` directory. The unchanged `dist` output is intentionally retained for Netlify and should not be used for the contact cutover.

The Function fails closed when its KV binding or email variables/secrets are absent, so no email is sent in the current unconfigured state. Do not submit a real customer enquiry until the provider, sender, recipient, origin allow-list, KV binding, and secrets have been configured and approved.

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
| Netlify redirects | None found. Cloudflare staging generates `.html` 301 rules and the Pages middleware enforces them when Functions handle the request. |
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
| `ALLOWED_ORIGINS` | variable | Set production to `https://doublepillarsconsultants.com,https://www.doublepillarsconsultants.com`; add a specific preview origin only when testing that preview. |
| `CONTACT_TO_EMAIL` | variable | Set to `doublepillars@gmail.com` in Preview and Production. |
| `CONTACT_FROM_EMAIL` | variable | Leave unchanged until a verified sending domain is available. |
| `CONTACT_RATE_LIMIT_MAX` | variable | Optional per-IP window limit; defaults to 5. |
| `CONTACT_RATE_LIMIT_WINDOW_SECONDS` | variable | Optional window; defaults to 900 seconds. |
| `RESEND_API_KEY` | encrypted secret | Sending-only provider key. |
| `CONTACT_RATE_LIMIT` | KV binding | KV namespace used for rate limiting. |

The form integration is staged in the Cloudflare candidate rather than applied to Netlify. A local/browser verification can exercise validation and the configured/unconfigured response without sending an enquiry. After Resend sender verification, the owner must approve one controlled test enquiry before live delivery.

The nine source pages already contain `doublepillars@gmail.com` in their contact information and structured data. No unrelated email addresses were changed, and the Resend API key is not stored in this repository.

## SEO and URL policy

The nine source pages use `.html` files, while Cloudflare production uses the official non-www origin and extensionless canonical URLs. The prepared strategy is:

1. Use the script's default official origin and extensionless mode to make extensionless URLs canonical.
2. Keep explicit 301 rules for all existing `.html` page URLs, preserving old bookmarks and inbound links.
3. Keep `pages.dev` previews `noindex`, and submit only `https://doublepillarsconsultants.com/sitemap.xml` after the cutover.

The staging copy changes URL metadata and internal links without changing the source files or existing Netlify `dist`.

The current SEO set uses one consistent official origin across all nine canonicals, Open Graph URLs, Twitter images, JSON-LD page URLs, `sitemap.xml`, and `robots.txt`. No Cloudflare preview address is promoted to a permanent business URL. The `pages.dev` noindex headers remain enabled.

## `www` redirect and custom-domain setup

Cloudflare Pages does not support domain-level host redirects in `_redirects`, and `_redirects` does not apply to requests served by Pages Functions. The root `functions/_middleware.js` therefore performs both of these safe 301 rules before the request reaches the site:

- `www.doublepillarsconsultants.com/*` → `https://doublepillarsconsultants.com/*`, preserving the path and query string;
- each legacy `.html` page path → its extensionless path, including the combined `www` + `.html` case in one hop.

Attach both custom hostnames to the same Pages project and ensure their DNS records are proxied before testing. The middleware only redirects the exact official `www` hostname, so the apex hostname cannot loop back to `www`.

## Resend sender verification required before live enquiries

The Resend test sender is not a production sender and cannot reliably deliver to arbitrary client addresses. Before switching live enquiry delivery:

1. In Resend, add `doublepillarsconsultants.com` under Domains.
2. Copy the exact verification and sending DNS records Resend shows into the authoritative Cloudflare DNS zone. Do not invent record values or create duplicate SPF records.
3. Wait for DNS propagation, then click Verify in Resend and confirm the domain has sending enabled.
4. Choose a sender address on the verified domain, then update `CONTACT_FROM_EMAIL` only after verification. Keep `CONTACT_TO_EMAIL=doublepillars@gmail.com`.
5. Keep `RESEND_API_KEY` in Cloudflare as an encrypted secret; do not put it in the repository or deployment command.
6. Run one separately approved controlled test enquiry, then monitor the Resend email log and the client mailbox.

Resend reports the required records and verification status in its Domains workflow; SPF and DKIM are set up as part of domain verification, while DMARC is recommended separately. See [Resend's domain-verification update](https://resend.com/changelog/domain-verification-events) and [deliverability guidance](https://resend.com/guides/email/deliverability/why-emails-go-to-spam).

## Netlify retirement preparation

Retirement is intentionally not performed in this repository. Keep both Netlify projects and the current Netlify deployment available as rollback options until all of the following are complete:

1. Attach `doublepillarsconsultants.com` and `www.doublepillarsconsultants.com` to the Pages project and confirm the official non-www canonical policy.
2. Configure Cloudflare Pages Preview and Production variables, KV binding, email provider, sender domain, and `CONTACT_TO_EMAIL=doublepillars@gmail.com`.
3. Verify `doublepillarsconsultants.com` in Resend before changing `CONTACT_FROM_EMAIL`; test the Cloudflare preview without submitting a real customer enquiry, then perform one separately approved controlled enquiry test.
4. Configure the custom domain and DNS cutover, verify HTTPS, redirects, headers, sitemap, robots, all nine pages, assets and the Function response.
5. Monitor the new deployment and preserve the Netlify rollback path for an agreed observation period.
6. Only after approval, export any required Netlify form records, disable Netlify build hooks, remove obsolete DNS references, and delete Netlify projects last.

No Netlify project, DNS record, rollback option, or form history was deleted.

## Required account access/approval

- Cloudflare account access to create/select the Pages project, set production/preview variables and secrets, bind KV, and configure the approved custom domain/DNS.
- An approved canonical production origin and redirect/URL policy.
- An approved email provider, verified sender domain, receiving mailbox, sending-only API key, and provider retention/privacy decision.
- Authorization for a non-production preview test, including one controlled test enquiry. This repository does not automatically change Cloudflare resources, DNS, dashboard settings or secrets, and automated verification never submits the contact form.
