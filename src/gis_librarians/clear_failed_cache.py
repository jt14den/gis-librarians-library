#!/usr/bin/env python3
"""Remove failed (empty) entries from the search cache so they can be retried."""

import json
from pathlib import Path

cache_file = Path("output/search_cache.json")
cache = json.loads(cache_file.read_text())

before = len(cache)
cache = {k: v for k, v in cache.items() if v}
after = len(cache)

cache_file.write_text(json.dumps(cache, indent=2))
print(f"Removed {before - after} failed entries, {after} kept")
