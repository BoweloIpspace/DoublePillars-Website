const OFFICIAL_HOST = "doublepillarsconsultants.com";
const WWW_HOST = `www.${OFFICIAL_HOST}`;

const LEGACY_PAGE_REDIRECTS = new Map([
  ["/index.html", "/"],
  ["/accounting-management.html", "/accounting-management"],
  ["/forensic-services.html", "/forensic-services"],
  ["/tax-advisory-compliance.html", "/tax-advisory-compliance"],
  ["/corporate-secretarial.html", "/corporate-secretarial"],
  ["/corporate-advisory.html", "/corporate-advisory"],
  ["/training.html", "/training"],
  ["/payroll-services.html", "/payroll-services"],
  ["/corporate-finance.html", "/corporate-finance"],
]);

function isPagesPreview(hostname) {
  return hostname.endsWith(".pages.dev");
}

function redirectResponse(target, isPreview) {
  const headers = new Headers({
    Location: target.toString(),
    "Cache-Control": "public, max-age=31536000, immutable",
  });
  if (isPreview) {
    headers.set("X-Robots-Tag", "noindex");
  }
  return new Response(null, { status: 301, headers });
}

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  const hostname = url.hostname.toLowerCase();
  const preview = isPagesPreview(hostname);
  const legacyPath = LEGACY_PAGE_REDIRECTS.get(url.pathname.toLowerCase());

  if (hostname === WWW_HOST || legacyPath) {
    const target = new URL(url.toString());
    target.protocol = "https:";
    if (hostname === WWW_HOST) {
      target.hostname = OFFICIAL_HOST;
    }
    if (legacyPath) {
      target.pathname = legacyPath;
    }
    return redirectResponse(target, preview);
  }

  const response = await next();
  if (!preview) {
    return response;
  }

  const headers = new Headers(response.headers);
  headers.set("X-Robots-Tag", "noindex");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}
