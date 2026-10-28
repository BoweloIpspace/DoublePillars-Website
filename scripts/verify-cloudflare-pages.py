"""Verify the static Cloudflare Pages staging/build output without network calls."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


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
ROOT_FILES = {"sitemap.xml", "robots.txt", "_headers"}


class PageParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids: set[str] = set()
        self.local_targets: list[str] = []
        self.images: list[tuple[str, str]] = []
        self.in_style = False
        self.style_text: list[str] = []
        self.feed(path.read_text(encoding="utf-8-sig"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        for attribute in ("href", "src"):
            target = values.get(attribute)
            if target:
                self.local_targets.append(target)
        if tag == "img" and values.get("src"):
            self.images.append((values["src"] or "", values.get("alt") or ""))
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.style_text.append(data)


def is_external(target: str) -> bool:
    parsed = urlsplit(target)
    return bool(parsed.scheme or parsed.netloc or target.startswith("//") or target.startswith("data:"))


def check_target(page: Path, root: Path, target: str, parsers: dict[str, PageParser], errors: list[str]) -> None:
    if is_external(target):
        return
    parsed = urlsplit(target)
    destination_name = unquote(parsed.path).lstrip("/")
    if not destination_name:
        destination_name = "index.html"
    destination = (root / destination_name).resolve()
    if not destination.is_file() and Path(destination_name).suffix == "":
        extensionless_page = (root / f"{destination_name}.html").resolve()
        if extensionless_page.is_file():
            destination = extensionless_page
    try:
        destination.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{page.name}: target escapes output directory: {target}")
        return
    if not destination.is_file():
        errors.append(f"{page.name}: missing local target: {target}")
        return
    if parsed.fragment and destination.name in parsers and unquote(parsed.fragment) not in parsers[destination.name].ids:
        errors.append(f"{page.name}: missing fragment target: {target}")


def check_redirects(root: Path, parsers: dict[str, PageParser], errors: list[str]) -> int:
    redirect_file = root / "_redirects"
    if not redirect_file.is_file():
        return 0
    count = 0
    for line_number, raw_line in enumerate(redirect_file.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) not in (2, 3) or parts[0][0:1] != "/" or parts[1][0:1] != "/":
            errors.append(f"_redirects:{line_number}: malformed redirect: {raw_line}")
            continue
        if len(parts) == 3 and parts[2] not in {"301", "302", "303", "307", "308"}:
            errors.append(f"_redirects:{line_number}: unsupported status: {parts[2]}")
        destination = parts[1].lstrip("/") or "index.html"
        destination_path = root / destination
        if not destination_path.is_file() and Path(destination).suffix == "":
            destination_path = root / f"{destination}.html"
        if not destination_path.is_file():
            errors.append(f"_redirects:{line_number}: missing destination: {parts[1]}")
        count += 1
    return count


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--root", default="dist", help="Output directory to verify")
    argument_parser.add_argument(
        "--expected-business-email",
        default="doublepillars@gmail.com",
        help="Business recipient that must appear in every page",
    )
    argument_parser.add_argument(
        "--expected-developer-credit",
        default="Developed by Bowelo Jobe",
        help="Developer credit that must appear exactly once on every page",
    )
    args = argument_parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: output directory does not exist: {root}")
        return 1

    errors: list[str] = []
    actual_pages = {path.name for path in root.glob("*.html")}
    if actual_pages != PAGE_NAMES:
        errors.append(f"expected exactly nine HTML pages; found {sorted(actual_pages)}")
    for file_name in ROOT_FILES:
        if not (root / file_name).is_file():
            errors.append(f"missing required root file: {file_name}")

    parsers = {name: PageParser(root / name) for name in sorted(actual_pages & PAGE_NAMES) if (root / name).is_file()}
    local_reference_count = 0
    email_verified_pages = 0
    credit_verified_pages = 0
    for page_name, parser in parsers.items():
        page = root / page_name
        page_text = page.read_text(encoding="utf-8-sig")
        if args.expected_business_email not in page_text:
            errors.append(f"{page_name}: expected business email is missing")
        else:
            email_verified_pages += 1
        credit_count = page_text.count(args.expected_developer_credit)
        if credit_count != 1:
            errors.append(
                f"{page_name}: expected developer credit exactly once; found {credit_count}"
            )
        else:
            credit_verified_pages += 1
        for target in parser.local_targets:
            local_reference_count += not is_external(target)
            check_target(page, root, target, parsers, errors)
        for css_text in parser.style_text:
            for target in re.findall(r"url\(\s*['\"]?([^)'\"]+)", css_text):
                check_target(page, root, target, parsers, errors)
        for source, alt in parser.images:
            if not alt.strip():
                errors.append(f"{page_name}: image is missing alt text: {source}")

    redirect_count = check_redirects(root, parsers, errors)

    routes_file = root / "_routes.json"
    if routes_file.is_file():
        staged_index = (root / "index.html").read_text(encoding="utf-8-sig")
        if "/api/contact" not in staged_index or "data-netlify" in staged_index or "netlify-honeypot" in staged_index:
            errors.append("staged index.html: Cloudflare contact transport is not cleanly wired")

    asset_directory = root / "assets"
    asset_count = len([path for path in asset_directory.iterdir() if path.is_file()]) if asset_directory.is_dir() else 0
    if asset_count != 35:
        errors.append(f"expected 35 published assets; found {asset_count}")

    if errors:
        print("\n".join(errors))
        return 1
    print(
        f"PASS: 9 HTML pages, {asset_count} assets, {local_reference_count} local HTTP references, "
        f"{redirect_count} redirects, business email on {email_verified_pages} pages, "
        f"developer credit on {credit_verified_pages} pages, fragments, CSS URLs and image alt text verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
