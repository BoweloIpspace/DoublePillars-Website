from pathlib import Path

css = """
<style id="nav-alignment-fix">
@media (min-width: 1100px) {
  header nav.desktop-nav {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 24px !important;
    margin: 0 auto !important;
    flex: 1 !important;
  }
  header .header-actions,
  header .nav-menu-item {
    flex-shrink: 0 !important;
  }
}
</style>
"""

for file in Path(".").glob("*.html"):
    if file.name == "index.html" or ".backup." in file.name:
        continue

    content = file.read_text(encoding="utf-8")

    if "desktop-nav" not in content:
        continue

    if "nav-alignment-fix" in content:
        continue

    if "</head>" not in content:
        continue

    file.write_text(
        content.replace("</head>", css + "\n</head>", 1),
        encoding="utf-8"
    )

    print("Updated:", file.name)
