#!/usr/bin/env python3
"""
merge_new_providers.py — Helper to merge new providers from fetch_providers.py output
into the main providers.json and rebuild the site.

Usage:
    python3 scripts/merge_new_providers.py

What this script does:
1. Reads data/new_providers_raw.json (output of fetch_providers.py)
2. Normalizes each entry to match providers.json schema
3. Shows each new provider and asks for confirmation
4. Appends confirmed entries to data/providers.json
5. Rebuilds the site by running: python3 build.py
"""

import json
import os
import re
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_PROVIDERS_JSON = os.path.join(ROOT, "data", "new_providers_raw.json")
PROVIDERS_JSON = os.path.join(ROOT, "data", "providers.json")
BUILD_SCRIPT = os.path.join(ROOT, "build.py")

# Required fields with their defaults
REQUIRED_FIELDS = {
    "name": "",
    "slug": "",
    "subtypes": "",
    "category": "Party equipment rental service",
    "rating": None,
    "reviews": None,
    "address": "",
    "street": "",
    "city": "Atlanta",
    "state": "Georgia",
    "postal": "",
    "lat": None,
    "lng": None,
    "about": "{}",
    "hours": None,
    "verified": False,
    # Enriched fields (optional but included if present)
    "place_id": "",
    "phone_direct": "",
    "website": "",
    "photos": [],
    "photo_refs": [],
}


def normalize_provider(raw):
    """Normalize a raw provider record to match providers.json schema."""
    record = {}
    for field, default in REQUIRED_FIELDS.items():
        val = raw.get(field, default)
        # Ensure correct types
        if field in ("rating",) and val is not None:
            try:
                val = float(val)
            except (TypeError, ValueError):
                val = None
        elif field in ("reviews",) and val is not None:
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = None
        elif field in ("lat", "lng") and val is not None:
            try:
                val = float(val)
            except (TypeError, ValueError):
                val = None
        elif field == "verified":
            val = bool(val)
        elif field in ("photos", "photo_refs") and not isinstance(val, list):
            val = []
        record[field] = val
    return record


def display_provider(p, index, total):
    """Print a provider record summary for review."""
    print(f"\n{'='*60}")
    print(f"Provider {index}/{total}: {p['name']}")
    print(f"{'='*60}")
    print(f"  Slug:     {p['slug']}")
    print(f"  Category: {p['category']}")
    print(f"  Address:  {p['address']}")
    print(f"  City:     {p['city']}, {p['state']} {p['postal']}")
    if p.get("rating"):
        print(f"  Rating:   {p['rating']} ({p.get('reviews', 0)} reviews)")
    if p.get("phone_direct"):
        print(f"  Phone:    {p['phone_direct']}")
    if p.get("website"):
        print(f"  Website:  {p['website']}")
    if p.get("photos"):
        print(f"  Photos:   {len(p['photos'])} photo(s)")
    print(f"  Subtypes: {p['subtypes'][:80] if p.get('subtypes') else '(none)'}")


def ask_confirm(prompt, default="y"):
    """Ask a yes/no question. Returns True for yes."""
    choices = "[Y/n]" if default == "y" else "[y/N]"
    while True:
        answer = input(f"{prompt} {choices}: ").strip().lower()
        if not answer:
            return default == "y"
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


def ask_choice(prompt, options):
    """Ask user to pick from a list. Returns selected option or None."""
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    print(f"  0. Skip this provider")
    while True:
        answer = input("Enter number: ").strip()
        if answer == "0":
            return None
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print("Invalid choice, try again.")


def slugify_unique(name, existing_slugs):
    """Generate a unique slug for the given name."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    base = s.strip("-")
    slug = base
    counter = 1
    while slug in existing_slugs:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def main():
    # Check new providers file exists
    if not os.path.exists(NEW_PROVIDERS_JSON):
        print(f"ERROR: {NEW_PROVIDERS_JSON} not found.")
        print("Run fetch_providers.py first to generate new provider data.")
        sys.exit(1)

    with open(NEW_PROVIDERS_JSON) as f:
        raw_new = json.load(f)

    if not raw_new:
        print("No new providers found in new_providers_raw.json.")
        sys.exit(0)

    # Load existing providers
    existing = []
    if os.path.exists(PROVIDERS_JSON):
        with open(PROVIDERS_JSON) as f:
            existing = json.load(f)

    existing_slugs = {p["slug"] for p in existing}
    existing_names = {p["name"].lower().strip() for p in existing}

    print(f"Found {len(raw_new)} new provider(s) to review.")
    print(f"Currently {len(existing)} provider(s) in providers.json.\n")

    confirmed = []

    for idx, raw in enumerate(raw_new, 1):
        # Normalize the record
        p = normalize_provider(raw)

        # Skip if name already exists in providers.json (shouldn't happen but guard it)
        if p["name"].lower().strip() in existing_names:
            print(f"\n[{idx}/{len(raw_new)}] SKIP (already exists): {p['name']}")
            continue

        # Ensure slug is unique
        if p["slug"] in existing_slugs:
            p["slug"] = slugify_unique(p["name"], existing_slugs)

        display_provider(p, idx, len(raw_new))

        if not ask_confirm(f"\nAdd '{p['name']}' to providers.json?"):
            print(f"  -> Skipped.")
            continue

        # Allow editing key fields before confirming
        if ask_confirm("  Edit any fields before adding?", default="n"):
            # Simple field editing
            for field in ["name", "slug", "city", "state", "postal", "category"]:
                current = p[field]
                new_val = input(f"  {field} [{current}]: ").strip()
                if new_val:
                    p[field] = new_val
                    if field == "name":
                        # Re-slugify if name changed
                        p["slug"] = slugify_unique(p["name"], existing_slugs)

        confirmed.append(p)
        existing_slugs.add(p["slug"])
        existing_names.add(p["name"].lower().strip())
        print(f"  -> Confirmed for addition: {p['name']!r}")

    if not confirmed:
        print("\nNo providers confirmed for addition. Exiting.")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"Confirmed {len(confirmed)} provider(s) to add.")

    if not ask_confirm(f"Append {len(confirmed)} provider(s) to providers.json and rebuild site?"):
        print("Aborted. No changes written.")
        sys.exit(0)

    # Append to providers.json
    updated = existing + confirmed
    with open(PROVIDERS_JSON, "w") as f:
        json.dump(updated, f, indent=1, ensure_ascii=False)
    print(f"\nWrote {len(updated)} providers to {PROVIDERS_JSON}")

    # Rebuild the site
    print("\nRebuilding site...")
    result = subprocess.run(
        [sys.executable, BUILD_SCRIPT],
        cwd=ROOT,
        capture_output=False,
    )
    if result.returncode == 0:
        print("\nSite rebuilt successfully.")
    else:
        print(f"\nWARNING: build.py exited with code {result.returncode}")
        print("Check the output above for errors.")

    print("\nDone.")
    print(f"  Added:    {len(confirmed)} new provider(s)")
    print(f"  Total:    {len(updated)} provider(s) in providers.json")


if __name__ == "__main__":
    main()
