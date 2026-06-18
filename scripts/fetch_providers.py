#!/usr/bin/env python3
"""
fetch_providers.py — Google Places API enrichment script for ATL Bounce House Rentals.

Usage:
    python3 scripts/fetch_providers.py --key YOUR_GOOGLE_PLACES_API_KEY

Or set the environment variable:
    GOOGLE_PLACES_API_KEY=YOUR_KEY python3 scripts/fetch_providers.py

What this script does:
1. Searches Google Places Text Search API for bounce/party rental businesses in Atlanta
2. Fetches Place Details for each unique place found (deduped by place_id)
3. Dedupes against existing providers.json by normalized name matching
4. Downloads provider photos to images/providers/<slug>/photo_N.jpg
5. Outputs new providers to data/new_providers_raw.json
6. Outputs enriched data for all existing providers to data/providers_enriched.json
7. Prints a summary of results
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip3 install requests")
    sys.exit(1)

# ------------------------------------------------------------------ paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVIDERS_JSON = os.path.join(ROOT, "data", "providers.json")
NEW_PROVIDERS_JSON = os.path.join(ROOT, "data", "new_providers_raw.json")
ENRICHED_JSON = os.path.join(ROOT, "data", "providers_enriched.json")
IMAGES_DIR = os.path.join(ROOT, "images", "providers")

# ------------------------------------------------------------------ API endpoints
TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"

# ------------------------------------------------------------------ search queries
SEARCH_QUERIES = [
    "bounce house rental Atlanta GA",
    "party rental Atlanta GA",
    "table and chair rental Atlanta GA",
    "inflatable rental Atlanta GA",
    "water slide rental Atlanta GA",
    "tent rental Atlanta GA",
    "concession rental Atlanta GA",
    "photo booth rental Atlanta GA",
    "silent disco rental Atlanta GA",
]

DETAIL_FIELDS = (
    "name,formatted_address,formatted_phone_number,website,"
    "rating,user_ratings_total,opening_hours,photos,types,geometry"
)


# ------------------------------------------------------------------ helpers
def normalize_name(name):
    """Normalize a business name for deduplication comparison."""
    if not name:
        return ""
    # Unicode normalize, lowercase, remove punctuation, collapse whitespace
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    n = n.lower()
    n = re.sub(r"[^\w\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    # Remove common suffixes for better matching
    for suffix in ["llc", "inc", "corp", "co", "company", "ltd"]:
        n = re.sub(rf"\b{suffix}\b", "", n).strip()
    return n


def slugify(name):
    """Convert a business name to a URL-safe slug."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def parse_address(formatted_address):
    """Parse a formatted_address string into components."""
    parts = {"street": "", "city": "", "state": "", "postal": ""}
    if not formatted_address:
        return parts
    # Try pattern: "Street, City, State ZIP, Country"
    m = re.match(
        r"^(.*?),\s*([^,]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?",
        formatted_address
    )
    if m:
        parts["street"] = m.group(1).strip()
        parts["city"] = m.group(2).strip()
        parts["state"] = m.group(3).strip()
        parts["postal"] = (m.group(4) or "").strip()
    return parts


def state_abbrev_to_full(abbrev):
    """Convert state abbreviation to full name."""
    mapping = {
        "GA": "Georgia", "AL": "Alabama", "FL": "Florida",
        "SC": "South Carolina", "NC": "North Carolina", "TN": "Tennessee",
    }
    return mapping.get(abbrev, abbrev)


# ------------------------------------------------------------------ API calls
def text_search(query, api_key, session):
    """Yield all place results for a Text Search query, handling pagination."""
    params = {
        "query": query,
        "type": "point_of_interest",
        "key": api_key,
    }
    page = 0
    while True:
        page += 1
        print(f"  [text_search] page {page} for: {query!r}")
        try:
            resp = session.get(TEXTSEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  WARNING: text_search request failed: {e}")
            break

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            print(f"  WARNING: text_search status={status} message={data.get('error_message', '')}")
            break

        results = data.get("results", [])
        print(f"    -> {len(results)} results")
        for r in results:
            yield r

        next_token = data.get("next_page_token")
        if not next_token:
            break
        # Google requires a short delay before using nextPageToken
        time.sleep(2.5)
        params = {"pagetoken": next_token, "key": api_key}


def fetch_place_details(place_id, api_key, session):
    """Fetch full place details for a given place_id. Returns dict or None."""
    params = {
        "place_id": place_id,
        "fields": DETAIL_FIELDS,
        "key": api_key,
    }
    try:
        resp = session.get(DETAILS_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  WARNING: place_details request failed for {place_id}: {e}")
        return None

    status = data.get("status")
    if status != "OK":
        print(f"  WARNING: place_details status={status} for {place_id}")
        return None

    return data.get("result", {})


def download_photo(photo_reference, api_key, session, dest_path, max_width=800):
    """Download a Places photo to dest_path. Returns True on success."""
    params = {
        "maxwidth": max_width,
        "photo_reference": photo_reference,
        "key": api_key,
    }
    try:
        resp = session.get(PHOTO_URL, params=params, timeout=30, stream=True)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  WARNING: photo download failed -> {dest_path}: {e}")
        return False


# ------------------------------------------------------------------ main logic
def collect_all_place_ids(queries, api_key, session):
    """Run all search queries and return a dict of {place_id: basic_result}."""
    seen = {}
    for query in queries:
        print(f"\nSearching: {query!r}")
        for result in text_search(query, api_key, session):
            pid = result.get("place_id")
            if pid and pid not in seen:
                seen[pid] = result
    print(f"\nTotal unique places found across all queries: {len(seen)}")
    return seen


def build_provider_record(place_id, details, photo_paths, photo_refs):
    """Convert a Place Details response into a providers.json-compatible record."""
    name = details.get("name", "")
    addr_str = details.get("formatted_address", "")
    addr_parts = parse_address(addr_str)
    state_full = state_abbrev_to_full(addr_parts["state"])

    geo = details.get("geometry", {}).get("location", {})
    lat = geo.get("lat")
    lng = geo.get("lng")

    types = details.get("types", [])
    subtypes = ", ".join(
        t.replace("_", " ").title()
        for t in types
        if t not in ("point_of_interest", "establishment", "geocode")
    )

    # Derive category from types
    type_set = set(types)
    if "event_planner" in type_set or "event_management" in type_set:
        category = "Event planner"
    elif "party_equipment_rental" in type_set or "party_store" in type_set:
        category = "Party equipment rental service"
    elif "amusement_park" in type_set or "amusement_center" in type_set:
        category = "Amusement center"
    elif "store" in type_set or "home_goods_store" in type_set:
        category = "Party supply store"
    else:
        # fallback: first non-generic type, prettified
        fallback = next(
            (t for t in types if t not in ("point_of_interest", "establishment", "geocode")),
            "party_rental"
        )
        category = fallback.replace("_", " ").title()

    hours_raw = details.get("opening_hours", {})
    weekday_text = hours_raw.get("weekday_text", [])
    hours_dict = {}
    day_map = {
        "Monday": "Monday", "Tuesday": "Tuesday", "Wednesday": "Wednesday",
        "Thursday": "Thursday", "Friday": "Friday", "Saturday": "Saturday", "Sunday": "Sunday",
    }
    for line in weekday_text:
        parts = line.split(": ", 1)
        if len(parts) == 2:
            day_abbrev = parts[0].strip()
            time_str = parts[1].strip()
            for day_full in day_map:
                if day_abbrev.startswith(day_full[:3]):
                    if time_str.lower() == "closed":
                        hours_dict[day_full] = []
                    else:
                        hours_dict[day_full] = [time_str]
                    break

    rating = details.get("rating")
    reviews = details.get("user_ratings_total")

    record = {
        "name": name,
        "slug": slugify(name),
        "subtypes": subtypes,
        "category": category,
        "rating": rating,
        "reviews": reviews,
        "address": addr_str,
        "street": addr_parts["street"],
        "city": addr_parts["city"],
        "state": state_full or addr_parts["state"],
        "postal": addr_parts["postal"],
        "lat": lat,
        "lng": lng,
        "about": "{}",
        "hours": json.dumps(hours_dict) if hours_dict else None,
        "verified": True,
        # Enriched fields
        "place_id": place_id,
        "phone_direct": details.get("formatted_phone_number") or "",
        "website": details.get("website") or "",
        "photos": photo_paths,
        "photo_refs": photo_refs,
    }
    return record


def enrich_existing_provider(it, details, photo_paths, photo_refs):
    """Add enriched fields to an existing provider record (in-place copy)."""
    enriched = dict(it)
    if details.get("formatted_phone_number") and not enriched.get("phone_direct"):
        enriched["phone_direct"] = details["formatted_phone_number"]
    if details.get("website") and not enriched.get("website"):
        enriched["website"] = details["website"]
    if photo_paths and not enriched.get("photos"):
        enriched["photos"] = photo_paths
    if photo_refs and not enriched.get("photo_refs"):
        enriched["photo_refs"] = photo_refs
    if details.get("place_id") and not enriched.get("place_id"):
        enriched["place_id"] = details.get("place_id", "")
    return enriched


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Google Places data to enrich ATL Bounce House Rentals provider directory."
    )
    parser.add_argument(
        "--key", "-k",
        default=os.environ.get("GOOGLE_PLACES_API_KEY", ""),
        help="Google Places API key (or set GOOGLE_PLACES_API_KEY env var)",
    )
    parser.add_argument(
        "--max-photos", type=int, default=3,
        help="Maximum number of photos to download per provider (default: 3)",
    )
    parser.add_argument(
        "--skip-photos", action="store_true",
        help="Skip downloading photos (faster, for testing)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run searches and print results without writing any files",
    )
    args = parser.parse_args()

    api_key = args.key.strip()
    if not api_key:
        print("ERROR: No API key provided. Use --key YOUR_KEY or set GOOGLE_PLACES_API_KEY.")
        sys.exit(1)

    # Load existing providers
    existing_providers = []
    if os.path.exists(PROVIDERS_JSON):
        with open(PROVIDERS_JSON) as f:
            existing_providers = json.load(f)
    print(f"Loaded {len(existing_providers)} existing providers from providers.json")

    # Build normalized name set for dedup
    existing_normalized = {normalize_name(p["name"]): p for p in existing_providers}
    existing_slugs = {p["slug"] for p in existing_providers}

    session = requests.Session()
    session.headers.update({"User-Agent": "ATLBounceHouseRentals-Enricher/1.0"})

    # Step 1: Collect all place_ids from search queries
    all_places = collect_all_place_ids(SEARCH_QUERIES, api_key, session)

    # Step 2: Fetch details for each place
    print("\nFetching Place Details...")
    new_providers = []
    enriched_existing = []

    # Track which existing providers we've matched for enrichment
    matched_existing_names = set()

    total = len(all_places)
    for idx, (place_id, basic) in enumerate(all_places.items(), 1):
        basic_name = basic.get("name", "")
        print(f"\n[{idx}/{total}] {basic_name!r} ({place_id})")

        details = fetch_place_details(place_id, api_key, session)
        if not details:
            print("  -> Skipping (no details)")
            continue

        name = details.get("name") or basic_name
        if not name:
            print("  -> Skipping (no name)")
            continue

        norm = normalize_name(name)

        # Check if this matches an existing provider
        matched_existing = existing_normalized.get(norm)
        is_new = matched_existing is None
        print(f"  -> {'NEW' if is_new else 'EXISTING: ' + matched_existing['name']}")

        # Download photos
        slug = slugify(name) if is_new else matched_existing["slug"]
        photos_raw = details.get("photos", [])[:args.max_photos]
        photo_paths = []
        photo_refs = []

        for i, photo_data in enumerate(photos_raw):
            ref = photo_data.get("photo_reference", "")
            if not ref:
                continue
            photo_refs.append(ref)
            rel_path = f"/images/providers/{slug}/photo_{i}.jpg"
            photo_paths.append(rel_path)

            if not args.skip_photos and not args.dry_run:
                abs_path = os.path.join(IMAGES_DIR, slug, f"photo_{i}.jpg")
                print(f"  Downloading photo {i} -> {abs_path}")
                download_photo(ref, api_key, session, abs_path)

        if is_new:
            # Build new provider record
            record = build_provider_record(place_id, details, photo_paths, photo_refs)
            # Ensure slug is unique
            base_slug = record["slug"]
            counter = 1
            while record["slug"] in existing_slugs or record["slug"] in {r["slug"] for r in new_providers}:
                record["slug"] = f"{base_slug}-{counter}"
                counter += 1
            new_providers.append(record)
            print(f"  -> Added as new provider: {record['name']!r} (slug: {record['slug']!r})")
        else:
            # Enrich existing provider
            if matched_existing["name"] not in matched_existing_names:
                enriched = enrich_existing_provider(
                    matched_existing, {"place_id": place_id, **details}, photo_paths, photo_refs
                )
                enriched_existing.append(enriched)
                matched_existing_names.add(matched_existing["name"])

        # Be polite to the API
        time.sleep(0.3)

    # Build enriched full list (existing providers with enrichments applied)
    enriched_by_name = {p["name"]: p for p in enriched_existing}
    providers_enriched = []
    for it in existing_providers:
        if it["name"] in enriched_by_name:
            providers_enriched.append(enriched_by_name[it["name"]])
        else:
            providers_enriched.append(it)

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  New providers found:        {len(new_providers)}")
    print(f"  Existing providers enriched: {len(enriched_existing)}")
    print(f"  Total existing providers:    {len(existing_providers)}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        if new_providers:
            print("\nNew providers that would be written:")
            for p in new_providers:
                print(f"  - {p['name']} ({p['city']}, {p['state']})")
        return

    # Write outputs
    if new_providers:
        with open(NEW_PROVIDERS_JSON, "w") as f:
            json.dump(new_providers, f, indent=2, ensure_ascii=False)
        print(f"\nWrote {len(new_providers)} new providers -> {NEW_PROVIDERS_JSON}")
    else:
        print("\nNo new providers to write.")

    with open(ENRICHED_JSON, "w") as f:
        json.dump(providers_enriched, f, indent=2, ensure_ascii=False)
    print(f"Wrote enriched data for {len(providers_enriched)} providers -> {ENRICHED_JSON}")

    print("\nDone. Next steps:")
    print("  1. Review data/new_providers_raw.json for new providers")
    print("  2. Run: python3 scripts/merge_new_providers.py to merge new providers")
    print("  3. Copy data/providers_enriched.json over data/providers.json if happy")
    print("  4. Run: python3 build.py to rebuild the site")


if __name__ == "__main__":
    main()
