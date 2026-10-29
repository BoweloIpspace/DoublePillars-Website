"""Validate the nine-page SEO metadata set for the official domain."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


PAGE_NAMES = {
    "index.html",
    "accounting-management.html",
    "forensic-services.html",
    "tax-advisory-compliance.html",
    "corporate-secretarial.html",
    "corporate-advisory.html",
    "training.html",
    "payroll-services.html",
    "corporate-finance.html",
}
SITEMAP_NAMESPACE = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class MetadataParser(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical: list[str] = []
        self.og_urls: list[str] = []
        self.json_ld: list[str] = []
        self.in_json_ld = False
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("rel", "").lower() == "canonical" and values.get("href"):
            self.canonical.append(values["href"] or "")
        if tag == "meta" and values.get("property", "").lower() == "og:url" and values.get("content"):
            self.og_urls.append(values["content"] or "")
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.in_json_ld = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.in_json_ld:
            self.in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self.in_json_ld:
            self.json_ld.append(data)


def json_values(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from json_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from json_values(child)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="dist")
    parser.add_argument("--expected-business-email", default="doublepillars@gmail.com")
    parser.add_argument("--expected-origin", default="https://doublepillarsconsultants.com")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []
    canonical_urls: set[str] = set()
    base_origins: set[str] = set()
    expected_origin = args.expected_origin.rstrip("/")

    for page_name in sorted(PAGE_NAMES):
        page = root / page_name
        if not page.is_file():
            errors.append(f"missing page: {page_name}")
            continue
        metadata = MetadataParser(page.read_text(encoding="utf-8-sig"))
        if len(metadata.canonical) != 1:
            errors.append(f"{page_name}: expected one canonical URL")
        if len(metadata.og_urls) != 1:
            errors.append(f"{page_name}: expected one og:url")
        if metadata.canonical and metadata.og_urls and metadata.canonical[0] != metadata.og_urls[0]:
            errors.append(f"{page_name}: canonical and og:url differ")
        if metadata.canonical:
            canonical = metadata.canonical[0]
            parsed = urlsplit(canonical)
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"{page_name}: canonical is not an HTTPS absolute URL")
            else:
                canonical_urls.add(canonical)
                base_origins.add(f"{parsed.scheme}://{parsed.netloc}")
                if f"{parsed.scheme}://{parsed.netloc}" != expected_origin:
                    errors.append(f"{page_name}: canonical origin must be {expected_origin}")
                if parsed.netloc.lower().startswith("www."):
                    errors.append(f"{page_name}: canonical must use the non-www official domain")
        if "doublepillars.netlify.app" in page.read_text(encoding="utf-8-sig"):
            errors.append(f"{page_name}: outdated Netlify URL remains")
        parsed_json = []
        for block in metadata.json_ld:
            try:
                parsed_json.append(json.loads(block))
            except json.JSONDecodeError as error:
                errors.append(f"{page_name}: invalid JSON-LD: {error.msg}")
        if not parsed_json:
            errors.append(f"{page_name}: missing JSON-LD")
        structured_emails = [
            item.get("email")
            for document in parsed_json
            for item in json_values(document)
            if isinstance(item, dict) and item.get("email")
        ]
        if args.expected_business_email not in structured_emails:
            errors.append(f"{page_name}: JSON-LD business email is missing")

    sitemap_path = root / "sitemap.xml"
    try:
        sitemap_root = ElementTree.parse(sitemap_path).getroot()
        sitemap_urls = {
            node.text or ""
            for node in sitemap_root.findall("s:url/s:loc", SITEMAP_NAMESPACE)
        }
        if sitemap_urls != canonical_urls:
            errors.append("sitemap URLs do not exactly match page canonicals")
    except (OSError, ElementTree.ParseError) as error:
        errors.append(f"invalid sitemap.xml: {error}")

    robots = (root / "robots.txt").read_text(encoding="utf-8-sig") if (root / "robots.txt").is_file() else ""
    sitemap_lines = [line.split(":", 1)[1].strip() for line in robots.splitlines() if line.lower().startswith("sitemap:")]
    if base_origins != {expected_origin}:
        errors.append(f"canonical origins must equal {{{expected_origin}}}")
    if len(base_origins) == 1 and sitemap_lines != [next(iter(base_origins)) + "/sitemap.xml"]:
        errors.append("robots.txt sitemap does not match the canonical origin")
    if "Disallow:" not in robots:
        errors.append("robots.txt has no Disallow directive")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"PASS: SEO metadata, JSON-LD email, sitemap and robots verified for {len(PAGE_NAMES)} pages; canonical origin preserved without assumption.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
