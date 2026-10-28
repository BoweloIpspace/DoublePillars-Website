const MAX_BODY_BYTES = 12_000;
const MAX_NAME_LENGTH = 120;
const MAX_COMPANY_LENGTH = 200;
const MAX_PHONE_LENGTH = 40;
const MAX_MESSAGE_LENGTH = 4_000;
const DEFAULT_RATE_LIMIT = 5;
const DEFAULT_RATE_WINDOW_SECONDS = 900;

const ALLOWED_SERVICES = new Set([
  "Business Accounting",
  "Taxation",
  "Advisory Services",
  "Forensic Accounting & Investigations",
  "Corporate Services",
  "Other",
]);

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=UTF-8",
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
      Vary: "Origin",
    },
  });
}

function normalizeOrigin(value) {
  try {
    const url = new URL(value);
    return `${url.protocol}//${url.host}`;
  } catch {
    return "";
  }
}

function allowedOrigins(env) {
  return String(env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((origin) => normalizeOrigin(origin.trim()))
    .filter(Boolean);
}

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}

function field(form, name) {
  return String(form.get(name) || "").trim();
}

function validateSubmission(form) {
  const submission = {
    fullName: field(form, "full-name"),
    company: field(form, "company"),
    email: field(form, "email"),
    phone: field(form, "phone"),
    service: field(form, "service-required"),
    message: field(form, "message"),
  };

  const errors = [];
  if (submission.fullName.length < 2 || submission.fullName.length > MAX_NAME_LENGTH) {
    errors.push("full-name");
  }
  if (submission.company.length > MAX_COMPANY_LENGTH) {
    errors.push("company");
  }
  if (submission.email.length > 254 || !EMAIL_PATTERN.test(submission.email)) {
    errors.push("email");
  }
  if (submission.phone.length < 3 || submission.phone.length > MAX_PHONE_LENGTH) {
    errors.push("phone");
  }
  if (!ALLOWED_SERVICES.has(submission.service)) {
    errors.push("service-required");
  }
  if (submission.message.length < 10 || submission.message.length > MAX_MESSAGE_LENGTH) {
    errors.push("message");
  }

  return { submission, errors };
}

async function applyRateLimit(request, env) {
  if (!env.CONTACT_RATE_LIMIT) {
    return { allowed: false, missingBinding: true };
  }

  const limit = Number(env.CONTACT_RATE_LIMIT_MAX || DEFAULT_RATE_LIMIT);
  const windowSeconds = Number(
    env.CONTACT_RATE_LIMIT_WINDOW_SECONDS || DEFAULT_RATE_WINDOW_SECONDS,
  );
  const clientAddress = request.headers.get("CF-Connecting-IP") || "unknown";
  const key = `contact:${clientAddress}`;
  const current = Number(await env.CONTACT_RATE_LIMIT.get(key) || 0);

  if (current >= limit) {
    return { allowed: false, missingBinding: false };
  }

  await env.CONTACT_RATE_LIMIT.put(key, String(current + 1), {
    expirationTtl: windowSeconds,
  });
  return { allowed: true, missingBinding: false };
}

export async function onRequest(context) {
  const { request, env } = context;

  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  const origin = normalizeOrigin(request.headers.get("Origin") || "");
  if (!origin || !allowedOrigins(env).includes(origin)) {
    return jsonResponse({ error: "Origin not allowed" }, 403);
  }

  const contentType = request.headers.get("Content-Type") || "";
  if (!contentType.toLowerCase().startsWith("application/x-www-form-urlencoded")) {
    return jsonResponse({ error: "Unsupported content type" }, 415);
  }

  const declaredLength = Number(request.headers.get("Content-Length") || 0);
  if (declaredLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "Request is too large" }, 413);
  }

  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "Request is too large" }, 413);
  }

  const form = new URLSearchParams(body);
  if (field(form, "bot-field")) {
    return new Response(null, { status: 204 });
  }

  const { submission, errors } = validateSubmission(form);
  if (errors.length) {
    return jsonResponse({ error: "Please check the required fields", fields: errors }, 400);
  }

  const rate = await applyRateLimit(request, env);
  if (rate.missingBinding) {
    console.error("CONTACT_RATE_LIMIT binding is not configured");
    return jsonResponse({ error: "Contact service is not configured" }, 503);
  }
  if (!rate.allowed) {
    return jsonResponse({ error: "Too many enquiries; please try again later" }, 429);
  }

  if (!env.RESEND_API_KEY || !env.CONTACT_TO_EMAIL || !env.CONTACT_FROM_EMAIL) {
    console.error("Contact email secrets/variables are not configured");
    return jsonResponse({ error: "Contact service is not configured" }, 503);
  }

  const text = [
    `Full name: ${submission.fullName}`,
    `Company/Organisation: ${submission.company || "Not provided"}`,
    `Email: ${submission.email}`,
    `Phone: ${submission.phone}`,
    `Service required: ${submission.service}`,
    "",
    submission.message,
  ].join("\n");
  const html = [
    `<p><strong>Full name:</strong> ${escapeHtml(submission.fullName)}</p>`,
    `<p><strong>Company/Organisation:</strong> ${escapeHtml(submission.company || "Not provided")}</p>`,
    `<p><strong>Email:</strong> ${escapeHtml(submission.email)}</p>`,
    `<p><strong>Phone:</strong> ${escapeHtml(submission.phone)}</p>`,
    `<p><strong>Service required:</strong> ${escapeHtml(submission.service)}</p>`,
    `<p><strong>Message:</strong><br>${escapeHtml(submission.message).replace(/\n/g, "<br>")}</p>`,
  ].join("");

  const providerResponse = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.CONTACT_FROM_EMAIL,
      to: [env.CONTACT_TO_EMAIL],
      reply_to: [submission.email],
      subject: `[Website enquiry] ${submission.service}`,
      text,
      html,
    }),
  });

  if (!providerResponse.ok) {
    console.error(`Email provider returned HTTP ${providerResponse.status}`);
    return jsonResponse({ error: "Unable to send enquiry" }, 502);
  }

  return jsonResponse({ ok: true });
}
