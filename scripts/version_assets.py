#!/usr/bin/env python3
"""Pin static CSS/JS URLs to their content hashes for GitHub Pages caches."""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = {
    "styles.css", "motion.css", "pagination.css", "orbit.css", "filters.css", "search.css", "history.css",
    "game.css", "gallery.css", "data.js", "app.js",
    "game.js", "history.js", "motion.js", "catalog-loader.js",
}
REFERENCE = re.compile(r'(?P<prefix>(?:href|src|data-after-catalog)=")(?P<name>[a-z0-9-]+\.(?:css|js))(?:\?v=[^"]+)?(?P<end>")')


def version(match):
    name = match.group("name")
    if name not in STATIC:
        return match.group(0)
    digest = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()[:12]
    return f'{match.group("prefix")}{name}?v={digest}{match.group("end")}'


for page in ("index.html", "game.html"):
    path = ROOT / page
    original = path.read_text(encoding="utf-8")
    updated = REFERENCE.sub(version, original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        print("Versioned", page)
