#!/usr/bin/env python3
"""Static-site generator for Atlanta Bounce House Rentals.
Reads data/providers.json and regenerates the whole site:
homepage, services, individual service pages, partners directory,
individual partner pages, leads board, legal pages, 404, sitemap.

Theme: light blue + black. No emojis. No ad placeholders.
Business phone/contact are never published — the site phone is shown instead.
Run: python3 build.py
"""
import json, os, re, html, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
PHONE_DISPLAY = "(401) 889-0182"
PHONE_HREF = "+14018890182"
OWN_BUSINESS_URL = "https://buy.stripe.com/3cIfZi96i6cM7My9pIfrW09"
DOMAIN = "https://atlbouncehouserentals.com"

SERVICES = {
    "classic-bounce-house-rentals": "Classic Bounce House Rentals",
    "bounce-and-slide-combo-rentals": "Bounce and Slide Combo Rentals",
    "water-slide-rentals": "Water Slide Rentals",
    "obstacle-course-rentals": "Obstacle Course Rentals",
    "concession-rentals": "Concession Rentals",
    "tents-tables-and-chair-rentals": "Tents, Tables and Chair Rentals",
    "interactive-rentals": "Interactive Rentals",
    "silent-disco-rentals": "Silent Disco Rentals",
    "photo-booth-rentals": "Photo Booth Rentals",
    "wedding-decor-rentals": "Wedding and Event Decor Rentals",
    "party-package-rentals": "Party Package Rentals",
    "party-entertainment-and-staff-rentals": "Party Entertainment and Staff Rentals",
}

# Compact labels for the directory table "Services" column.
SERVICES_SHORT = {
    "classic-bounce-house-rentals": "Bounce Houses",
    "bounce-and-slide-combo-rentals": "Combos",
    "water-slide-rentals": "Water Slides",
    "obstacle-course-rentals": "Obstacle Courses",
    "concession-rentals": "Concessions",
    "tents-tables-and-chair-rentals": "Tents & Tables",
    "interactive-rentals": "Interactive",
    "silent-disco-rentals": "Silent Disco",
    "photo-booth-rentals": "Photo Booths",
    "wedding-decor-rentals": "Wedding Decor",
    "party-package-rentals": "Party Packages",
    "party-entertainment-and-staff-rentals": "Entertainment & Staff",
}

KEYWORDS = [
    (["water slide", "waterslide", "water-slide", "splash", "slip"], "water-slide-rentals"),
    (["combo", "bounce and slide", "bounce & slide", "slide combo"], "bounce-and-slide-combo-rentals"),
    (["obstacle", "course"], "obstacle-course-rentals"),
    (["concession", "popcorn", "cotton candy", "snow cone", "snowcone", "shaved ice", "frozen drink"], "concession-rentals"),
    (["tent", "table", "chair", "canopy", "linen"], "tents-tables-and-chair-rentals"),
    (["silent disco", "silent party", "headphone party", "silent headphone"], "silent-disco-rentals"),
    (["photo booth", "photobooth", "360 booth", "360 photo", "roaming photo"], "photo-booth-rentals"),
    (["wedding decor", "wedding rental", "wedding linen", "event decor", "drapery", "floral"], "wedding-decor-rentals"),
    (["arcade", "amusement", "game", "interactive", "dunk", "carnival", "mechanical", "axe", "laser"], "interactive-rentals"),
    (["dj", "bartend", "bartending", "entertainer", "entertainment", "host", "character", "costume", "clown", "face paint", "balloon", "limousine", "limo", "staff", "magician", "videograph", "catering", "caterer", "petting", "pony"], "party-entertainment-and-staff-rentals"),
    (["bounce", "jump", "jumper", "moonwalk", "moon walk", "inflatable", "bouncer", "bouncy", "castle"], "classic-bounce-house-rentals"),
    (["package", "party rental", "party equipment", "event rental", "event planner", "event management", "party planner", "party supply"], "party-package-rentals"),
]

# Finer-grained tags shown as extra searchmap filter chips, layered on top of
# the core SERVICES categories above. Not full service pages — just richer
# filtering/labeling for the map, so a listing can carry both the broad
# "Tents & Tables" tag and a specific "Chair Rentals" or "Tent Rentals" one.
MAP_EXTRA_KEYWORDS = [
    (["chair"], "Chair Rentals"),
    (["tent", "canopy"], "Tent Rentals"),
    (["table"], "Table Rentals"),
]


def extra_map_tags(it):
    hay = " ".join([it["name"], it["subtypes"], it["category"]]).lower()
    tags = [label for words, label in MAP_EXTRA_KEYWORDS if any(w in hay for w in words)]
    if "classic-bounce-house-rentals" in it.get("services", []):
        tags.append("$99 Bounce House Rentals")
    return tags

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Real Atlanta ZIP codes present in the listings, mapped to their common area names.
ZIP_AREAS = {
    "30303": "Downtown Atlanta", "30307": "Inman Park / Candler Park", "30308": "Midtown / Old Fourth Ward",
    "30309": "Midtown", "30310": "West End", "30311": "Cascade Heights", "30312": "Grant Park / Cabbagetown",
    "30314": "Vine City", "30315": "South Atlanta / Lakewood", "30316": "East Atlanta / Reynoldstown",
    "30317": "Kirkwood / East Lake", "30318": "West Midtown", "30319": "Brookhaven",
    "30324": "Morningside / Lindbergh", "30326": "Buckhead (Lenox)", "30327": "Buckhead (Northwest)",
    "30328": "Sandy Springs", "30329": "North Druid Hills", "30331": "Southwest Atlanta",
    "30336": "Adamsville / Fulton Industrial", "30339": "Cumberland / Vinings", "30340": "Doraville",
    "30341": "Chamblee", "30342": "Sandy Springs (Buckhead North)", "30344": "East Point",
    "30349": "College Park", "30350": "Sandy Springs (North)", "30360": "Dunwoody / Peachtree Corners",
}


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def map_services(it):
    hay = " ".join([it["name"], it["subtypes"], it["category"]]).lower()
    found = [slug for words, slug in KEYWORDS if any(w in hay for w in words)]
    if not found:
        found = ["party-package-rentals"]
    return [s for s in SERVICES if s in found]


def stars(rating):
    if not rating:
        return ""
    full = int(round(float(rating)))
    return "★" * full + "☆" * (5 - full)


def prov_meta_html(p):
    """Star rating + review count for a provider list item, e.g.
    ' — ★★★★☆ 4.5 (13 reviews)' or ' — 13 reviews' if unrated."""
    if p.get("rating"):
        stars_html = f' — <span class="li-stars">{stars(p["rating"])}</span> {p["rating"]}'
        if p.get("reviews"):
            stars_html += f' ({p["reviews"]} reviews)'
        return stars_html
    if p.get("reviews"):
        return f' — {p["reviews"]} reviews'
    return ""


# ----------------------------------------------------------------- featured images
# Real photos (supplied directly, not stock/generated) used as a featured image on
# every generated page. Each entry is (path, default alt text, width, height).
FEATURED_IMAGES = {
    "bounce_house": ("/images/hero-bounce-house.jpg",
                      "Bounce house and slide combo set up for a birthday party in metro Atlanta, Georgia", 1376, 768),
    "tent_luxury": ("/images/gallery/luxury-poolside-tent-event.jpg",
                     "Elegant poolside event tents set up for a celebration in Atlanta, Georgia", 1600, 1069),
    "kids_tables": ("/images/gallery/pink-kids-party-tables-chairs.jpg",
                     "Folding tables and chairs set up for a kids' birthday party in an Atlanta backyard", 1600, 1066),
    "boho_tent": ("/images/gallery/boho-tent-fall-event.jpg",
                  "Rustic tent with wood folding chairs and tables set up for an outdoor Atlanta event", 435, 459),
    "gold_ballroom": ("/images/gallery/luxury-white-gold-ballroom.jpg",
                       "Elegant white and gold chair and table setup for a formal Atlanta event", 481, 637),
}
DEFAULT_FEATURED_IMAGE = "tent_luxury"

# Maps a core SERVICES slug or /find/ family url_prefix to a FEATURED_IMAGES key.
# Anything not listed here falls back to DEFAULT_FEATURED_IMAGE, so every page
# that calls featured_image_html() still gets a real photo.
IMAGE_KEY_BY_SLUG = {
    "classic-bounce-house-rentals": "bounce_house",
    "tents-tables-and-chair-rentals": "tent_luxury",
    "wedding-decor-rentals": "gold_ballroom",
    "chiavari-chair-rentals": "gold_ballroom",
    "throne-chair-rentals": "gold_ballroom",
    "ghost-chair-rentals": "gold_ballroom",
    "cocktail-table-rentals": "tent_luxury",
    "farmhouse-table-rentals": "boho_tent",
    "kids-table-and-chair-rentals": "kids_tables",
    "bounce-house-rentals": "bounce_house",
    "99-bounce-house-rentals": "bounce_house",
    "tents-table-chair-rentals": "tent_luxury",
    "event-table-rentals": "tent_luxury",
    "event-chair-rentals": "gold_ballroom",
    "table-rentals": "kids_tables",
    "chair-rentals": "gold_ballroom",
    "tent-rentals": "boho_tent",
    "folding-chair-rentals": "kids_tables",
    "kids-party-rentals": "kids_tables",
    "back-to-school-party-rentals": "boho_tent",
    "gender-reveal-party-event-rentals": "kids_tables",
}


def featured_image_html(key=None, alt_override=None, cls="content-photo"):
    """<img> tag for a real featured photo. key may be a FEATURED_IMAGES key,
    a SERVICES slug, or a /find/ url_prefix — anything unrecognized falls back
    to the default photo so every page that calls this still gets an image."""
    if key not in FEATURED_IMAGES:
        key = IMAGE_KEY_BY_SLUG.get(key, DEFAULT_FEATURED_IMAGE)
    src, alt, w, h = FEATURED_IMAGES[key]
    alt_text = alt_override or alt
    return f'<img class="{cls}" src="{src}" alt="{esc(alt_text)}" loading="lazy" width="{w}" height="{h}">'


def parse_attrs(about_json):
    bits = []
    try:
        for grp in json.loads(about_json).values():
            if isinstance(grp, dict):
                for k, v in grp.items():
                    if v is True and k not in bits:
                        bits.append(k)
    except Exception:
        pass
    return bits


def about_text(it, services):
    cat = it["category"].lower()
    names = [SERVICES[s] for s in services]
    phrase = (", ".join(names[:-1]) + " and " + names[-1]) if len(names) > 1 else names[0]
    rating, reviews = it["rating"], it["reviews"]
    rev = ""
    if rating and reviews:
        rev = f" The company holds a {rating}-star rating across {reviews} Google reviews from local customers."
    elif reviews:
        rev = f" The company has earned {reviews} Google reviews from local customers."
    attrs = [a for a in parse_attrs(it["about"]) if any(t in a.lower() for t in ["owned", "veteran", "lgbtq", "wheelchair", "online appointment", "onsite"])]
    attr = (" Notable highlights include " + ", ".join(a.lower() for a in attrs[:3]) + ".") if attrs else ""
    return (f"{it['name']} is a trusted {cat} serving {it['city']}, {it['state']} and the surrounding "
            f"Atlanta metro area.{rev} Through the Atlanta Bounce House Rentals directory you can request "
            f"availability and pricing for {phrase.lower()}.{attr} To check open dates or get a free quote "
            f"for your event, call {PHONE_DISPLAY}.")


def hours_map(it):
    data = {}
    if it["hours"]:
        try:
            data = json.loads(it["hours"])
        except Exception:
            data = {}
    out = {}
    for d in DAYS:
        v = data.get(d)
        if isinstance(v, list):
            out[d] = ", ".join(v) if v else "Closed"
        elif v:
            out[d] = str(v)
        elif data:
            out[d] = "Closed"
    return out


def hours_rows(it):
    m = hours_map(it)
    rows = []
    for d in DAYS:
        txt = m.get(d, "Call to confirm")
        rows.append(f'<tr data-day="{d}"><td class="day">{d}</td><td>{esc(txt)}</td></tr>')
    return "\n        ".join(rows)


def map_embed(it):
    if it["lat"] and it["lng"]:
        q = f'{it["lat"]},{it["lng"]}'
    else:
        q = (it["address"] or (it["name"] + " Atlanta GA")).replace(" ", "+")
    return f"https://www.google.com/maps?q={q}&z=15&output=embed"


# ----------------------------------------------------------------- shells
def header(active=""):
    def cls(name):
        return ' class="active"' if name == active else ""
    return f'''<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/"><img class="brand-logo" src="/images/favicon.svg" alt="" width="40" height="40"><span><span class="brand-accent">Atlanta</span> Bounce House Rentals</span></a>
    <div class="header-right">
      <nav class="main-nav" aria-label="Primary">
        <a href="/"{cls("home")}>Home</a>
        <a href="/find/"{cls("find")}>Find</a>
      </nav>
      <a class="book-now-cta" href="#" data-wizard-open>Book Now</a>
      <button class="nav-toggle" aria-label="Open menu" aria-expanded="false">&#9776;</button>
    </div>
  </div>
</header>'''


FOOTER = f'''<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div>
        <div class="footer-brand">Atlanta Bounce House Rentals</div>
        <p>Your trusted directory for bounce house and party rentals across Atlanta, Georgia.</p>
        <p><a href="tel:{PHONE_HREF}"><strong>{PHONE_DISPLAY}</strong></a></p>
      </div>
      <div>
        <h4>Top Services</h4>
        <a href="/services/classic-bounce-house-rentals/">Classic Bounce Houses</a>
        <a href="/services/water-slide-rentals/">Water Slides</a>
        <a href="/services/obstacle-course-rentals/">Obstacle Courses</a>
        <a href="/services/silent-disco-rentals/">Silent Disco Rentals</a>
        <a href="/services/photo-booth-rentals/">Photo Booth Rentals</a>
        <a href="/services/party-package-rentals/">Party Packages</a>
        <a href="/services/">All Services</a>
      </div>
      <div>
        <h4>Directory</h4>
        <a href="/">Home</a>
        <a href="/services/">Services</a>
        <a href="/bounce-houses/">Bounce Houses for Rent</a>
        <a href="/locations/">Service Areas</a>
        <a href="/cheap-bounce-house-rentals/">Cheap Bounce House Rentals</a>
        <a href="/partners.html">Partners</a>
        <a href="/leads.html">Leads</a>
      </div>
      <div>
        <h4>Company</h4>
        <a href="/legal/about.html">About Us</a>
        <a href="/legal/contact.html">Contact</a>
        <a href="/legal/privacy-policy.html">Privacy Policy</a>
        <a href="/legal/terms.html">Terms of Service</a>
        <a href="/legal/disclaimer.html">Disclaimer</a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; <span data-year>2026</span> Atlanta Bounce House Rentals. All rights reserved.</span>
      <span>Atlanta, Georgia &middot; <a href="/legal/privacy-policy.html">Privacy</a> &middot; <a href="/legal/terms.html">Terms</a></span>
    </div>
  </div>
</footer>'''

def trust_strip(count=None, extra_class=""):
    """Small badge row reinforcing we're a trusted, fast-responding directory.
    Pass the live provider count where available so the number never goes stale."""
    provider_badge = f'<span>&#9989; {count} vetted Atlanta providers</span>' if count else '<span>&#9989; Vetted Atlanta providers</span>'
    return f'''<div class="trust-strip{" " + extra_class if extra_class else ""}">
      <span>&#11088; Trusted Atlanta directory</span>
      {provider_badge}
      <span>&#9201;&#65039; Fast, free quotes</span>
      <span>&#128274; Your info is never sold</span>
    </div>'''


ADSENSE = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2173008413459742" crossorigin="anonymous"></script>'

# Leaflet CSS/JS for the interactive search map. Loaded only on pages that use it.
LEAFLET_HEAD = ('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" '
                'integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">\n')
LEAFLET_JS = ('<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" '
              'integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>')


def searchmap_html(area="", lat=None, lng=None, zoom=11, limit=0, service=""):
    """Return the search-map container. JS in /js/searchmap.js hydrates it from
    window.ABHR_PROVIDERS. Optional lat/lng/zoom centers it on a city.
    Optional service pre-filters providers to only those offering that service
    (matches the SERVICES_SHORT label used in map-data.js)."""
    attrs = f' data-area="{esc(area)}" data-zoom="{zoom}"'
    if lat is not None and lng is not None:
        attrs += f' data-lat="{lat:.5f}" data-lng="{lng:.5f}"'
    if limit:
        attrs += f' data-limit="{limit}"'
    if service:
        attrs += f' data-service="{esc(service)}"'
    return f'<div class="searchmap" data-searchmap{attrs}></div>'


def build_map_data(providers):
    """Write /js/map-data.js exposing a compact provider array for the search map.
    Loading it as a script (not fetch) keeps the map working on any static host."""
    compact = []
    for p in providers:
        if not (p.get("lat") and p.get("lng")):
            continue
        compact.append({
            "name": p["name"],
            "slug": p["slug"],
            "lat": round(float(p["lat"]), 6),
            "lng": round(float(p["lng"]), 6),
            "rating": p.get("rating") or 0,
            "reviews": p.get("reviews") or 0,
            "city": p.get("city") or "Atlanta",
            "category": p.get("category") or "Party rentals",
            "services": [SERVICES_SHORT[s] for s in p.get("services", []) if s in SERVICES_SHORT] + extra_map_tags(p),
        })
    js = "window.ABHR_PROVIDERS = " + json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(ROOT, "js", "map-data.js"), "w").write(js)


# Geographic centers for each metro city/district, used when no directory
# provider ZIP falls inside the area (so the map still centers correctly).
CITY_CENTERS = {
    "buckhead": (33.8484, -84.3781), "midtown": (33.7838, -84.3830),
    "downtown-atlanta": (33.7550, -84.3900), "decatur": (33.7748, -84.2963),
    "sandy-springs": (33.9304, -84.3733), "dunwoody": (33.9462, -84.3346),
    "roswell": (34.0232, -84.3616), "alpharetta": (34.0754, -84.2941),
    "marietta": (33.9526, -84.5499), "smyrna": (33.8840, -84.5144),
    "kennesaw": (34.0234, -84.6155), "brookhaven": (33.8651, -84.3366),
    "chamblee": (33.8920, -84.2988), "vinings": (33.8651, -84.4649),
    "west-midtown": (33.7900, -84.4120), "east-atlanta": (33.7407, -84.3419),
    "west-end": (33.7381, -84.4180), "east-point": (33.6795, -84.4394),
    "college-park": (33.6534, -84.4494), "stone-mountain": (33.8082, -84.1702),
    "lawrenceville": (33.9562, -83.9880), "johns-creek": (34.0289, -84.1986),
}


def location_center(loc, providers):
    """City map center: mean lat/lng of matched providers, falling back to the
    city's true geographic center, then to metro Atlanta."""
    matched = providers_for_location(loc, providers, limit=50)
    pts = [(float(p["lat"]), float(p["lng"])) for p in matched if p.get("lat") and p.get("lng")]
    if pts:
        return (sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts))
    return CITY_CENTERS.get(loc["slug"], (33.749, -84.388))


def faq_block(faqs):
    """Return (visible HTML section, FAQPage JSON-LD) for a list of (q, a) pairs."""
    if not faqs:
        return "", ""
    items = "\n      ".join(
        f'''<details class="faq-item">
        <summary>{esc(q)}</summary>
        <div class="faq-a">{a}</div>
      </details>''' for q, a in faqs)
    section = f'''
<section class="alt" id="faq">
  <div class="container content" style="max-width:820px;">
    <div class="eyebrow">FAQ</div>
    <h2>Frequently Asked Questions</h2>
    <div class="faq">
      {items}
    </div>
  </div>
</section>'''
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in faqs]}
    return section, f'<script type="application/ld+json">\n{json.dumps(ld, ensure_ascii=False)}\n</script>\n'


def head(title, desc, canonical, extra=""):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="icon" type="image/svg+xml" href="/images/favicon.svg">
<link rel="apple-touch-icon" href="/images/favicon.svg">
<meta name="author" content="Atlanta Bounce House Rentals">
<meta name="geo.region" content="US-GA">
<meta name="geo.placename" content="Atlanta, Georgia">
<meta name="theme-color" content="#3a93d6">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Atlanta Bounce House Rentals">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{DOMAIN}/images/hero-bounce-house.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{DOMAIN}/images/hero-bounce-house.jpg">
<link rel="stylesheet" href="/css/style.css">
{ADSENSE}
{extra}</head>
<body>
'''


# ----------------------------------------------------------------- provider table
def provider_rows(providers):
    rows = []
    for it in providers:
        svc_names = [SERVICES[s] for s in it["services"]]
        search = " ".join([it["name"], it["subtypes"], it["category"]] + svc_names + [it["city"]]).lower()
        search = esc(re.sub(r"\s+", " ", search))
        rating = it["rating"]
        if rating:
            rate_html = f'<span class="star">&#9733;</span>{rating}'
        else:
            rate_html = '<span class="muted">&mdash;</span>'
        ver = '<span class="yes">Yes</span>' if it["verified"] else '<span class="no">&mdash;</span>'
        loc = esc(f'{it["city"]}, {it["state"]}')
        svc_short = ", ".join(SERVICES_SHORT[s] for s in it["services"]) or "&mdash;"
        rows.append(f'''        <tr data-search="{search}">
          <td class="biz"><a href="/partners/{it["slug"]}/">{esc(it["name"])}</a><span class="loc">{loc}</span></td>
          <td class="rating">{rate_html}</td>
          <td class="num">{it["reviews"]}</td>
          <td class="verified">{ver}</td>
          <td class="svc">{svc_short}</td>
          <td class="book"><button type="button" class="table-book-btn" data-wizard-open aria-label="Book {esc(it["name"])}">Book Now</button></td>
        </tr>''')
    return "\n".join(rows)


def provider_table(providers, search_id="dir-search"):
    return f'''    <div class="dir-tools">
      <input type="search" id="{search_id}" placeholder="Search providers by name, service or area..." aria-label="Search providers">
      <span class="dir-count" id="{search_id}-count">{len(providers)} providers</span>
    </div>
    <div class="table-wrap">
      <table class="provider-table" id="provider-table">
        <thead>
          <tr><th>Contractor</th><th>Rating</th><th class="num">Reviews</th><th>Verified</th><th>Services</th><th></th></tr>
        </thead>
        <tbody>
{provider_rows(providers)}
          <tr id="no-results" style="display:none;"><td colspan="6" class="no-results">No providers match your search. Call {PHONE_DISPLAY} and we'll find one for you.</td></tr>
        </tbody>
      </table>
    </div>'''


# ----------------------------------------------------------------- homepage
def coverage_areas(providers):
    """Distinct real areas covered, derived from listing ZIP codes, ordered by count."""
    counts = {}
    for it in providers:
        z = str(it.get("postal") or "").strip()
        area = ZIP_AREAS.get(z)
        if area:
            counts[area] = counts.get(area, 0) + 1
    return [a for a, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def build_index(providers):
    svc_links = "\n      ".join(
        f'<li><a href="/services/{s}/">{SERVICES[s]} in Atlanta Georgia</a></li>' for s in SERVICES)
    areas = coverage_areas(providers)
    area_links = "\n      ".join(
        f'<li><a href="{location_href(l)}">Bounce House Rentals in {esc(l["name"])}</a></li>'
        for l in LOCATIONS)
    chips = "\n          ".join(
        f'<button type="button" data-q="{SERVICES[s].lower()}">{SERVICES[s]}</button>' for s in SERVICES)

    faqs = [
        ("How much does it cost to rent a bounce house in Atlanta?",
         "<p>In Atlanta, a classic bounce house typically rents for about $120&ndash;$260 per day, while larger combo units, water slides and obstacle courses range from roughly $180 to $900+ depending on size. Full party packages run from around $220 to $1,800+. Final pricing depends on the date, delivery distance, rental length and add-ons. <a href=\"/#providers\">Request a free quote</a> for an exact figure.</p>"),
        ("How do I book a bounce house rental in Atlanta?",
         "<p>Click <a href=\"#\" data-wizard-open>Book Now</a> in the header or at the top of this page. Tell us your event type, date, ZIP code and what you need, and we'll match you with available Atlanta directory providers so you can compare and book.</p>"),
        ("What areas around Atlanta do you serve?",
         "<p>Our directory providers serve the City of Atlanta and the surrounding metro, including Midtown, Buckhead, Downtown, Decatur, Sandy Springs, College Park, East Point, Dunwoody, Chamblee and more.</p>"),
        ("What types of bounce houses and party rentals are available?",
         "<p>You can rent classic bounce houses, bounce-and-slide combos, water slides, obstacle courses, concession machines, tents, tables and chairs, interactive games, complete party packages and event staff. See the <a href=\"/services/\">full list of services</a>.</p>"),
        ("Are the rental providers verified?",
         "<p>Yes. Each provider listing shows whether the business is verified on Google along with its star rating and review count, so you can choose a trusted, well-reviewed Atlanta company with confidence.</p>"),
        ("How far in advance should I book a bounce house in Atlanta?",
         "<p>For weekends in spring and summer&mdash;Atlanta's busiest party season&mdash;book 2 to 4 weeks ahead. Water slides and large combos sell out fastest. For last-minute needs, <a href=\"#\" data-wizard-open>book now</a> and we'll check live availability.</p>"),
    ]
    faq_html, faq_ld = faq_block(faqs)

    extra = f'''<script type="application/ld+json">
{json.dumps({"@context":"https://schema.org","@type":"Organization","name":"Atlanta Bounce House Rentals","url":DOMAIN+"/","logo":DOMAIN+"/images/logo.svg","telephone":PHONE_HREF,"areaServed":{"@type":"City","name":"Atlanta"},"contactPoint":{"@type":"ContactPoint","telephone":PHONE_HREF,"contactType":"customer service","areaServed":"US","availableLanguage":"English"}}, ensure_ascii=False)}
</script>
<script type="application/ld+json">
{json.dumps({"@context":"https://schema.org","@type":"WebSite","name":"Atlanta Bounce House Rentals","url":DOMAIN+"/","potentialAction":{"@type":"SearchAction","target":{"@type":"EntryPoint","urlTemplate":DOMAIN+"/partners.html?q={{search_term_string}}"},"query-input":"required name=search_term_string"}}, ensure_ascii=False)}
</script>
<script type="application/ld+json">
{json.dumps({"@context":"https://schema.org","@type":"LocalBusiness","name":"Atlanta Bounce House Rental Directory","telephone":PHONE_HREF,"url":DOMAIN+"/","areaServed":{"@type":"City","name":"Atlanta"},"address":{"@type":"PostalAddress","addressLocality":"Atlanta","addressRegion":"GA","addressCountry":"US"}}, ensure_ascii=False)}
</script>
{faq_ld}
{LEAFLET_HEAD}'''
    html_out = head(
        "Atlanta Bounce House Rental Directory | Connect With All Providers And Compare",
        "Atlanta Bounce House Rental directory connecting you with all local providers. Search by service, compare bounce houses, water slides, obstacle courses and party rentals across Atlanta, Georgia. Free quotes.",
        DOMAIN + "/", extra)
    html_out += header("home") + f'''
<section id="map">
  <div class="container">
    <h1 style="text-align: center; margin-bottom: 0.4em; font-size: 2.1rem;">Atlanta Bounce House Rental Directory</h1>
    <p style="text-align: center; max-width: 800px; margin: 0 auto 26px; font-size: 1.1rem;">Find and book bounce houses, water slides and party rentals from {len(providers)} trusted providers across Atlanta, Georgia.</p>
    {searchmap_html(area="Atlanta", zoom=10)}
  </div>
</section>

<section id="services">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">What You Can Rent</div>
      <h2>All Bounce House Rental Services In Atlanta Georgia</h2>
      <p>Explore every rental category available across the Atlanta metro and request a free quote on any of them.</p>
    </div>
    <img class="content-photo" src="/images/hero-bounce-house.jpg" alt="Colorful bounce house and slide combo set up in a backyard for a birthday party in Atlanta, Georgia" loading="lazy" width="1376" height="768">
    <ul class="bullet-services">
      {svc_links}
    </ul>
  </div>
</section>

<section class="alt" id="service-area">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Service Area</div>
      <h2>Bounce House Rentals Across Metro Atlanta</h2>
      <p>The {len(providers)} providers in our directory serve every corner of the Atlanta metro. Choose your city or neighborhood to see local providers and pricing:</p>
    </div>
    <ul class="bullet-services bullet-cols" style="margin-bottom:24px;">
      {area_links}
    </ul>
    <p style="text-align:center;"><a class="btn btn-outline" href="/locations/">View All Service Areas</a></p>
  </div>
</section>

<section id="providers">
  <div class="container">
    <div class="section-head flex">
      <div>
        <div class="eyebrow">The Directory</div>
        <h2>Bounce House &amp; Party Rental Providers in Atlanta Georgia</h2>
      </div>
      <a class="view-all" href="/partners.html">View all {len(providers)} &#8599;</a>
    </div>
{provider_table(providers)}
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Ready to Book Your Atlanta Bounce House Rental?</h2>
    <p>Tell us about your event and we'll match you with available Atlanta providers in minutes. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/main.js"></script>
<script src="/js/directory.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    open(os.path.join(ROOT, "index.html"), "w").write(html_out)


# ----------------------------------------------------------------- partners directory
def build_partners(providers):
    html_out = head(
        "Atlanta Bounce House Rental Providers Directory | Partners",
        f"Directory of {len(providers)} bounce house and party rental providers serving Atlanta, Georgia. Compare ratings, reviews and verification, then call for a free quote.",
        DOMAIN + "/partners.html")
    html_out += header("partners") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Partners</div>
    <h1>Atlanta Bounce House &amp; Party Rental Providers</h1>
    <p>Browse {len(providers)} bounce house and party rental businesses serving Atlanta and the surrounding Georgia metro. Compare ratings and reviews, then click Book Now to tell us about your event and get matched with the right provider.</p>
  </div>
</div>

<section>
  <div class="container">
    {featured_image_html(alt_override="Atlanta party rental providers set up for a celebration")}
{provider_table(providers)}
    <div class="callout" style="margin-top:26px;">
      <p><strong>Ready to book?</strong> Use the <a href="#" data-wizard-open>Book Now</a> wizard to tell us about your event and we'll connect you with an available Atlanta company in minutes. Free quotes, no obligation.</p>
    </div>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/directory.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    open(os.path.join(ROOT, "partners.html"), "w").write(html_out)


# ----------------------------------------------------------------- partner pages
def build_partner_pages(providers):
    by_cat = {}
    for it in providers:
        by_cat.setdefault(it["category"], []).append(it)

    for it in providers:
        name, slug = it["name"], it["slug"]
        services = it["services"]
        about = about_text(it, services)
        title = f"{name} {it['city']} {it['state']}"
        desc = about[:155].replace('"', "'")
        svc_tags = "\n          ".join(f'<a href="/services/{s}/">{SERVICES[s]}</a>' for s in services)

        similar = [x for x in by_cat.get(it["category"], []) if x["slug"] != slug][:6]
        if len(similar) < 4:
            for x in providers:
                if x["slug"] != slug and x not in similar:
                    similar.append(x)
                if len(similar) >= 6:
                    break
        sim_html = "\n        ".join(
            f'<li><a href="/partners/{x["slug"]}/">{esc(x["name"])}</a><span class="muted"> &mdash; {esc(x["category"])}</span></li>'
            for x in similar)

        verified = ('<span class="verified-badge">Verified on Google</span>' if it["verified"]
                    else '<span class="unverified-badge">Listing from Google</span>')
        rating_html = ""
        if it["rating"]:
            rating_html = (f'<span class="rating-inline"><span class="stars">{stars(it["rating"])}</span> '
                           f'{it["rating"]} ({it["reviews"]} Google reviews)</span>')
        elif it["reviews"]:
            rating_html = f'<span class="rating-inline">{it["reviews"]} Google reviews</span>'
        addr = esc(it["address"]) or esc(f'{it["city"]}, {it["state"]}')

        ld = {
            "@context": "https://schema.org", "@type": "LocalBusiness", "name": name,
            "address": {"@type": "PostalAddress", "streetAddress": it["street"], "addressLocality": it["city"],
                        "addressRegion": it.get("state", ""), "postalCode": it["postal"], "addressCountry": "US"},
            "telephone": PHONE_HREF, "url": f"{DOMAIN}/partners/{slug}/",
            "areaServed": {"@type": "City", "name": "Atlanta"},
        }
        if it["rating"] and it["reviews"]:
            ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": it["rating"], "reviewCount": it["reviews"]}
        if it["lat"] and it["lng"]:
            ld["geo"] = {"@type": "GeoCoordinates", "latitude": it["lat"], "longitude": it["lng"]}
        extra = f'<script type="application/ld+json">\n{json.dumps(ld, ensure_ascii=False)}\n</script>\n'

        partner_photo = featured_image_html(
            services[0] if services else None,
            alt_override=f"{name} — party rental services in {it['city']}, {it['state']}")

        page = head(esc(title), desc, f"{DOMAIN}/partners/{slug}/", extra)
        page += header("partners") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/partners.html">Partners</a> &rsaquo; {esc(name)}</div>
    <h1>{esc(name)}</h1>
    <div class="partner-meta">
      {verified}
      {rating_html}
      <span class="muted">{addr}</span>
    </div>
    {trust_strip(count=len(providers))}
  </div>
</div>

<section>
  <div class="container">
    <div class="grid" style="grid-template-columns:1.6fr 1fr; gap:40px; align-items:start;">
      <div class="content">
        <h2>About {esc(name)}</h2>
        {partner_photo}
        <p>{esc(about)}</p>

        <h2>Services Offered</h2>
        <p>Through our directory, {esc(name)} can be booked for the following Atlanta party rental services. Select any service to see pricing and request a quote:</p>
        <div class="svc-tags">
          {svc_tags}
        </div>

        <h2>Location</h2>
        <p class="muted" style="margin-bottom:14px;">{addr}</p>
        <div class="map-wrap">
          <iframe title="Map showing {esc(name)} in {esc(it["city"])}, {esc(it["state"])}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="{map_embed(it)}"></iframe>
        </div>

        <h2 style="margin-top:36px;">Similar Providers in Atlanta</h2>
        <ul>
        {sim_html}
        </ul>
        <p><a href="/partners.html">&larr; Back to the full partner directory</a></p>
      </div>

      <aside>
        <div class="quote-card" style="margin-bottom:22px;">
          <h2>Book This Provider</h2>
          <p class="sub">Tell us about your event and we'll get you a quote from {esc(name)} and other available Atlanta providers &mdash; usually within minutes.</p>
          <a class="btn btn-block" href="#" data-wizard-open>Book Now &rsaquo;</a>
          <div class="hero-trust" style="margin-top:14px;justify-content:center;">
            <span>Free quotes</span>
            <span>No obligation</span>
            <span>Fast response</span>
            <span>Info kept private</span>
          </div>
        </div>

        <div class="info-box">
          <h3>Business Hours</h3>
          <table class="hours">
        {hours_rows(it)}
          </table>
          <p class="muted" style="font-size:0.8rem;margin:12px 0 0;">Hours from Google. Call to confirm holiday availability.</p>
        </div>

        <div class="info-box own-business-box">
          <h3>Are You {esc(name)}?</h3>
          <p class="muted" style="font-size:0.88rem;">Claim this listing to update your info, add photos and get priority placement in the directory.</p>
          <a class="btn btn-block" href="{OWN_BUSINESS_URL}" target="_blank" rel="noopener">Own This Business &rsaquo;</a>
        </div>
      </aside>
    </div>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/partners.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        d = os.path.join(ROOT, "partners", slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(page)


# ----------------------------------------------------------------- service pages
SERVICE_CONTENT = json.load(open(os.path.join(ROOT, "data", "service-content.json"))) if os.path.exists(os.path.join(ROOT, "data", "service-content.json")) else None

LOCATIONS = json.load(open(os.path.join(ROOT, "data", "locations.json"))) if os.path.exists(os.path.join(ROOT, "data", "locations.json")) else []
LOC_BY_SLUG = {l["slug"]: l for l in LOCATIONS}


def providers_for_location(loc, providers, limit=12):
    """Providers whose listing ZIP falls within this location's ZIP set, best first."""
    zset = set(loc.get("zips", []))
    matched = [p for p in providers if str(p.get("postal") or "").strip() in zset]
    matched.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
    return matched[:limit]


# Cities with at least one matched provider get a full programmatic /find/
# page instead of a /locations/ page (populated in main() before any builder
# that links to a location runs). Cities with zero matched providers keep
# their /locations/ page as a general, provider-list-free landing page.
MIGRATED_LOCATION_SLUGS = set()


def location_href(loc):
    """Where a link to this location should point — /find/ if it has been
    migrated to a programmatic page, otherwise the original /locations/ page."""
    slug = loc["slug"]
    if slug in MIGRATED_LOCATION_SLUGS:
        return f"/find/bounce-house-rentals-{slug}-ga/"
    return f"/locations/{slug}/"



def build_service_pages(providers):
    data = SERVICE_CONTENT
    for s in data:
        slug = s["slug"]
        others = "\n            ".join(
            f'<li><a href="/services/{x}/">{SERVICES[x]}</a></li>' for x in SERVICES if x != slug)
        loc_links = "\n            ".join(
            f'<li><a href="{location_href(l)}">{SERVICES[slug]} in {esc(l["name"])}</a></li>'
            for l in LOCATIONS[:12])
        offering = [p for p in providers if slug in p["services"]]
        offering.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
        providers_links = "\n            ".join(
            f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a></li>' for p in offering)
        options = "\n              ".join(
            f'<option value="{SERVICES[x]}"{" selected" if x == slug else ""}>{SERVICES[x]}</option>' for x in SERVICES)
        prices = "\n          ".join(
            f'''<div class="price-card{" featured" if i == 1 else ""}">
            <div class="tier">{p["tier"]}</div>
            <div class="amount">{p["amount"]} <span>{p["sub"]}</span></div>
            <ul>
              {"".join(f"<li>{it}</li>" for it in p["items"])}
            </ul>
          </div>''' for i, p in enumerate(s["prices"]))
        body = "\n        ".join(f"<p>{p}</p>" for p in s["body"])
        ld = {"@context": "https://schema.org", "@type": "Service", "serviceType": s["name"],
              "areaServed": {"@type": "City", "name": "Atlanta"},
              "provider": {"@type": "LocalBusiness", "name": "Atlanta Bounce House Rental Directory", "telephone": PHONE_HREF},
              "url": f"{DOMAIN}/services/{slug}/"}
        bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Services", "item": DOMAIN + "/services/"},
            {"@type": "ListItem", "position": 3, "name": s["name"], "item": f"{DOMAIN}/services/{slug}/"}]}
        nm = s["name"]
        nml = nm.lower()
        lo = s["prices"][0]["amount"]
        hi = s["prices"][-1]["amount"]
        faqs = [
            (f"How much do {nml} cost in Atlanta?",
             f"<p>In the Atlanta area, {nml} typically range from {lo} for a small event up to {hi} for the largest setups. The final price depends on your date, the unit size, delivery distance and rental length. <a href=\"/#providers\">Request a free quote</a> for exact pricing.</p>"),
            (f"How do I book {nml} in Atlanta?",
             f"<p>Click <a href=\"#\" data-wizard-open>Book Now</a> to tell us about your event. We'll match you with available Atlanta providers that offer {nml} for your date.</p>"),
            (f"Do providers deliver {nml} across metro Atlanta?",
             f"<p>Yes. Directory providers deliver {nml} to Atlanta and surrounding areas including Midtown, Buckhead, Decatur, Sandy Springs, College Park and East Point, and they handle setup and pickup.</p>"),
            (f"How far in advance should I reserve {nml}?",
             f"<p>Booking 2&ndash;4 weeks ahead is recommended for weekend dates in Atlanta's busy spring and summer season. Last-minute requests are welcome too&mdash;<a href=\"#\" data-wizard-open>book now</a> and we'll check live availability.</p>"),
        ]
        faq_html, faq_ld = faq_block(faqs)
        extra = (f'<script type="application/ld+json">\n{json.dumps(ld, ensure_ascii=False)}\n</script>\n'
                 f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}')

        page = head(f'{s["name"]} In Atlanta Georgia', s["intro"][:155].replace('"', "'"),
                    f"{DOMAIN}/services/{slug}/", extra)
        page += header("services") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/services/">Services</a> &rsaquo; {s["name"]}</div>
    <h1>{s["h1"]}</h1>
    <p>{s["intro"]}</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="grid" style="grid-template-columns:1.6fr 1fr; gap:48px; align-items:start;">
      <div class="content">
        <h2>About {s["name"]} in Atlanta</h2>
        {body}

        <div class="callout">
          <p><strong>Serving all of metro Atlanta.</strong> Providers in our directory deliver {s["name"].lower()} to Atlanta, Buckhead, Midtown, Decatur, Sandy Springs, Marietta, Roswell, East Point and surrounding Georgia communities.</p>
        </div>

        <h2>{s["name"]} Price Estimates in Atlanta</h2>
        <p>Below are typical Atlanta price ranges for {s["name"].lower()} by event size. Final pricing depends on the date, delivery distance, rental duration and add-ons. Request a free quote for an exact figure.</p>
        <div class="price-grid">
          {prices}
        </div>

        <h2>Atlanta Providers Offering {s["name"]}</h2>
        <p>The following directory providers handle {s["name"].lower()} in the Atlanta area. Select a provider to view details, or call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> for a free quote:</p>
        <ul class="bullet-services">
            {providers_links}
        </ul>

        <h2>{s["name"]} by Atlanta Area</h2>
        <p>We connect you with providers offering {s["name"].lower()} across the metro:</p>
        <ul class="bullet-services">
            {loc_links}
            <li><a href="/locations/">View all service areas</a></li>
        </ul>

        <h2>Other Bounce House Rental Services in Atlanta</h2>
        <ul>
            {others}
        </ul>
      </div>

      <aside>
        <div class="quote-card" style="position:sticky; top:90px;">
          <h2>Free Quote</h2>
          <p class="sub">Request pricing for {s["name"].lower()} in Atlanta.</p>
          <form data-quote-form novalidate>
            <div data-success class="form-success" style="display:none;">
              Thanks! A provider will contact you shortly. Call <strong>{PHONE_DISPLAY}</strong> for immediate help.
            </div>
            <div data-fields>
              <div class="field"><label for="q-name">Full Name</label><input id="q-name" name="name" type="text" required></div>
              <div class="field"><label for="q-phone">Phone</label><input id="q-phone" name="phone" type="tel" required></div>
              <div class="field"><label for="q-email">Email</label><input id="q-email" name="email" type="email" required></div>
              <div class="field"><label for="q-service">Service</label>
                <select id="q-service" name="service">
              {options}
                </select>
              </div>
              <div class="field"><label for="q-date">Event Date</label><input id="q-date" name="event_date" type="date"></div>
              <div class="field"><label for="q-zip">ZIP Code</label><input id="q-zip" name="zip" type="text" placeholder="30303"></div>
              <button class="btn btn-block" type="submit">Get My Free Quote</button>
              <p class="form-note">Or call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a></p>
            </div>
          </form>
        </div>
      </aside>
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Book {s["name"]} in Atlanta Today</h2>
    <p>Compare available Atlanta providers and lock in your date. Free quotes, no obligation.</p>
    <a class="btn" href="tel:{PHONE_HREF}">Call {PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
</body>
</html>
'''
        d = os.path.join(ROOT, "services", slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(page)


# ----------------------------------------------------------------- bounce houses
def build_bounce_houses():
    items = json.load(open(os.path.join(ROOT, "data", "bounce-houses.json")))

    # --- index page ---
    cards = []
    for it in items:
        from_price = it["pricing"][0]["price"]
        has_img = True  # placeholder toggle; real check would test file existence
        img_html = (f'<img class="bh-card-img" src="{it["images"][0]}" alt="{esc(it["name"])} rental in Atlanta, Georgia" loading="lazy" width="600" height="450">'
                    if has_img else
                    f'<div class="bh-card-img-placeholder">Image coming soon</div>')
        cards.append(f'''    <a class="bh-card" href="/bounce-houses/{it["slug"]}/">
      {img_html}
      <div class="bh-card-body">
        <div class="bh-cat">{esc(it["category"])}</div>
        <h3>{esc(it["name"])}</h3>
        <p class="bh-from">From <strong>${from_price}</strong> &middot; Setup &amp; teardown included</p>
      </div>
    </a>''')
    cards_html = "\n".join(cards)

    idx = head(
        "Bounce Houses for Rent in Atlanta Georgia | ATL Bounce House Rentals",
        "Browse bounce houses available for rent across Atlanta, Georgia. Classic castles, rainbow combos and more — setup and teardown included. Call (401) 889-0182 for pricing and availability.",
        DOMAIN + "/bounce-houses/")
    idx += header("bounce-houses") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Bounce Houses</div>
    <h1>Bounce Houses for Rent in Atlanta, Georgia</h1>
    <p>Browse our selection of inflatable bounce houses available for rent across Atlanta and the surrounding metro. All units include delivery, setup and teardown. Call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> or request a quote below for pricing and availability.</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="bh-grid">
{cards_html}
    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Need Help Choosing the Right Bounce House?</h2>
    <p>Tell us about your event — guest count, date, venue — and we'll match you with the perfect unit and best price.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "bounce-houses")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(idx)

    # --- detail pages ---
    for it in items:
        pricing_rows = []
        for tier in it["pricing"]:
            featured_cls = " featured" if tier["featured"] else ""
            pricing_rows.append(f'''          <div class="bh-tier{featured_cls}">
            <div class="bh-tier-label">{esc(tier["tier"])}<small>{esc(tier["label"])}</small></div>
            <div class="bh-tier-price">${esc(tier["price"])}</div>
          </div>''')
        pricing_html = "\n".join(pricing_rows)

        included_html = "\n".join(f"<li>{esc(i)}</li>" for i in it["included"])
        you_need_html = "\n".join(f"<li>{esc(i)}</li>" for i in it["you_need"])
        policies_html = "\n".join(f"<li>{esc(p)}</li>" for p in it["policies"])

        imgs = it.get("images", [])
        gallery_html = "\n".join(
            f'<img src="{esc(src)}" alt="{esc(it["name"])} rental in Atlanta, Georgia' +
            (' — product view' if i == 0 else ' set up for a backyard party') + '" loading="lazy">'
            for i, src in enumerate(imgs)
        ) if imgs else f'<div class="bh-gallery-placeholder">Photos coming soon — call {PHONE_DISPLAY} to see more.</div>'

        ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": it["name"],
            "description": it["tagline"],
            "image": [DOMAIN + src for src in imgs],
            "brand": {"@type": "Brand", "name": "Atlanta Bounce House Rentals"},
            "offers": {
                "@type": "Offer",
                "priceCurrency": "USD",
                "price": it["pricing"][0]["price"],
                "availability": "https://schema.org/InStock",
                "seller": {"@type": "Organization", "name": "Atlanta Bounce House Rentals", "telephone": PHONE_HREF}
            }
        }, ensure_ascii=False)

        extra = f'<script type="application/ld+json">\n{ld}\n</script>'

        page = head(
            f'{it["name"]} Rental Atlanta Georgia | ATL Bounce House Rentals',
            f'Rent the {it["name"]} in Atlanta, Georgia. {it["tagline"]} Starting at ${it["pricing"][0]["price"]}. Call (401) 889-0182 or request a quote.',
            f'{DOMAIN}/bounce-houses/{it["slug"]}/',
            extra)
        page += header("bounce-houses") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/bounce-houses/">Bounce Houses</a> &rsaquo; {esc(it["name"])}</div>
    <h1>{esc(it["name"])} Rental</h1>
    <p>{esc(it["tagline"])}</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="bh-detail">

      <!-- Left: gallery + specs -->
      <div>
        <div class="bh-gallery">
          {gallery_html}
        </div>

        <h2 style="margin-top:34px;">Product Details</h2>

        <dl class="bh-specs" style="margin-bottom:28px;">
          <div class="bh-spec"><dt>Item Dimensions</dt><dd>{esc(it["dimensions_item"])}</dd></div>
          <div class="bh-spec"><dt>Space Needed</dt><dd>{esc(it["dimensions_space"])}</dd></div>
          <div class="bh-spec"><dt>Circuits</dt><dd>{it["circuits"]}</dd></div>
          <div class="bh-spec"><dt>Max Occupancy</dt><dd>{esc(it["max_occupancy"])}</dd></div>
        </dl>

        <h3>What&rsquo;s Included</h3>
        <ul class="bh-policy-list" style="margin-bottom:24px;">
          {included_html}
        </ul>

        <h3>What You&rsquo;ll Need</h3>
        <ul class="bh-policy-list" style="margin-bottom:24px;">
          {you_need_html}
        </ul>

        <h3>Policies &amp; Notes</h3>
        <ul class="bh-policy-list">
          {policies_html}
        </ul>
      </div>

      <!-- Right: pricing + contact -->
      <div class="bh-info">
        <div class="bh-pricing-card">
          <h3>Pricing</h3>
{pricing_html}
          <ul class="bh-inclusions">
            <li>All prices include setup and teardown</li>
            <li>Reserve with just a ${it["deposit"]} deposit</li>
            <li>{it["extra_per_hour_pct"]}% extra per additional hour</li>
          </ul>
        </div>

        <div class="bh-contact-card">
          <h3>Get Pricing &amp; Reserve</h3>
          <p class="sub">Tell us about your event and we&rsquo;ll confirm availability and send you a quote in minutes.</p>
          <a class="btn btn-block" href="#" data-wizard-open style="margin-bottom:14px;">Book Now &rsaquo;</a>
          <div class="bh-or">— or fill out the form —</div>
          <form data-quote-form novalidate>
            <div data-success class="form-success" style="display:none;">
              Thanks! We received your request for the {esc(it["name"])}. We&rsquo;ll be in touch shortly. Need it sooner? Call <strong>{PHONE_DISPLAY}</strong>.
            </div>
            <div data-fields>
              <div class="field"><label for="q-name">Full Name</label><input id="q-name" name="name" type="text" required></div>
              <div class="field"><label for="q-phone">Phone</label><input id="q-phone" name="phone" type="tel" required></div>
              <div class="field"><label for="q-email">Email</label><input id="q-email" name="email" type="email" required></div>
              <input type="hidden" name="item" value="{esc(it["name"])}">
              <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div><label for="q-date">Event Date</label><input id="q-date" name="event_date" type="date"></div>
                <div><label for="q-zip">ZIP Code</label><input id="q-zip" name="zip" type="text" placeholder="30303"></div>
              </div>
              <div class="field"><label for="q-msg">Message (optional)</label><textarea id="q-msg" name="message" rows="3" placeholder="Any questions or details about your event..."></textarea></div>
              <button class="btn btn-block" type="submit">Request a Quote</button>
            </div>
          </form>
        </div>
      </div>

    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Ready to Book?</h2>
    <p>Tell us about your event and we'll confirm availability and lock in your date. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        slug_dir = os.path.join(ROOT, "bounce-houses", it["slug"])
        os.makedirs(slug_dir, exist_ok=True)
        open(os.path.join(slug_dir, "index.html"), "w").write(page)


# ----------------------------------------------------------------- locations


SPECIALTY_SLUGS = [
    ("chiavari-chair-rentals", "Chiavari Chair Rentals Atlanta"),
    ("ghost-chair-rentals", "Ghost Chair Rentals Atlanta"),
    ("kids-table-and-chair-rentals", "Kids Table and Chair Rentals Atlanta"),
    ("farmhouse-table-rentals", "Farmhouse Table Rentals Atlanta"),
    ("throne-chair-rentals", "Throne Chair Rentals Atlanta"),
    ("cocktail-table-rentals", "Cocktail Table Rentals Atlanta"),
    ("slushy-machine-rentals", "Slushy Machine and Snow Cone Rentals Atlanta"),
]


def build_services_index():
    links = "\n      ".join(
        f'<li><a href="/services/{s}/">{SERVICES[s]} in Atlanta Georgia</a></li>' for s in SERVICES)
    specialty_links = "\n      ".join(
        f'<li><a href="/services/{slug}/">{name}</a></li>' for slug, name in SPECIALTY_SLUGS)
    html_out = head(
        "Bounce House Rental In Atlanta Georgia",
        "Browse every Bounce House Rental service in Atlanta, Georgia. Classic bounce houses, water slides, obstacle courses, concessions, tents, party packages and more with free quotes.",
        DOMAIN + "/services/")
    html_out += header("services") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Services</div>
    <h1>Bounce House Rental In Atlanta Georgia</h1>
    <p>Explore every bounce house and party rental service available across Atlanta, Georgia. Select any service below to view price estimates and request a free quote.</p>
  </div>
</div>

<section>
  <div class="container content" style="max-width:none;">
    <h2>All Bounce House Rental Services in Atlanta</h2>
    {featured_image_html(alt_override="Bounce house and party rental equipment set up for an Atlanta event")}
    <ul class="bullet-services">
      {links}
    </ul>
    <h2>Specialty Rental Equipment</h2>
    <p>Deep-dive pages for specific event equipment popular at Atlanta weddings, corporate events and parties:</p>
    <ul class="bullet-services">
      {specialty_links}
    </ul>
    <div class="callout">
      <p><strong>Not sure what you need?</strong> Use the Book Now wizard and tell us about your event — we'll match you with the right Atlanta providers and equipment for your date.</p>
    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Get a Free Atlanta Bounce House Quote</h2>
    <p>Tell us about your event and we'll match you with available Atlanta providers in minutes.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    open(os.path.join(ROOT, "services", "index.html"), "w").write(html_out)


def build_service_pages(providers):
    data = SERVICE_CONTENT
    for s in data:
        slug = s["slug"]
        others = "\n            ".join(
            f'<li><a href="/services/{x}/">{SERVICES[x]}</a></li>' for x in SERVICES if x != slug)
        loc_links = "\n            ".join(
            f'<li><a href="{location_href(l)}">{SERVICES[slug]} in {esc(l["name"])}</a></li>'
            for l in LOCATIONS[:12])
        offering = [p for p in providers if slug in p["services"]]
        offering.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
        providers_links = "\n            ".join(
            f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a></li>' for p in offering)
        options = "\n              ".join(
            f'<option value="{SERVICES[x]}"{" selected" if x == slug else ""}>{SERVICES[x]}</option>' for x in SERVICES)
        prices = "\n          ".join(
            f'''<div class="price-card{" featured" if i == 1 else ""}">
            <div class="tier">{p["tier"]}</div>
            <div class="amount">{p["amount"]} <span>{p["sub"]}</span></div>
            <ul>
              {"".join(f"<li>{it}</li>" for it in p["items"])}
            </ul>
          </div>''' for i, p in enumerate(s["prices"]))
        body = "\n        ".join(f"<p>{p}</p>" for p in s["body"])
        ld = {"@context": "https://schema.org", "@type": "Service", "serviceType": s["name"],
              "areaServed": {"@type": "City", "name": "Atlanta"},
              "provider": {"@type": "LocalBusiness", "name": "Atlanta Bounce House Rental Directory", "telephone": PHONE_HREF},
              "url": f"{DOMAIN}/services/{slug}/"}
        bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Services", "item": DOMAIN + "/services/"},
            {"@type": "ListItem", "position": 3, "name": s["name"], "item": f"{DOMAIN}/services/{slug}/"}]}
        nm = s["name"]
        nml = nm.lower()
        lo = s["prices"][0]["amount"]
        hi = s["prices"][-1]["amount"]
        faqs = [
            (f"How much do {nml} cost in Atlanta?",
             f"<p>In the Atlanta area, {nml} typically range from {lo} for a small event up to {hi} for the largest setups. The final price depends on your date, the unit size, delivery distance and rental length. <a href=\"/#providers\">Request a free quote</a> for exact pricing.</p>"),
            (f"How do I book {nml} in Atlanta?",
             f"<p>Click <a href=\"#\" data-wizard-open>Book Now</a> to tell us about your event. We'll match you with available Atlanta providers that offer {nml} for your date.</p>"),
            (f"Do providers deliver {nml} across metro Atlanta?",
             f"<p>Yes. Directory providers deliver {nml} to Atlanta and surrounding areas including Midtown, Buckhead, Decatur, Sandy Springs, College Park and East Point, and they handle setup and pickup.</p>"),
            (f"How far in advance should I reserve {nml}?",
             f"<p>Booking 2&ndash;4 weeks ahead is recommended for weekend dates in Atlanta's busy spring and summer season. Last-minute requests are welcome too&mdash;<a href=\"#\" data-wizard-open>book now</a> and we'll check live availability.</p>"),
        ]
        faq_html, faq_ld = faq_block(faqs)
        extra = (f'<script type="application/ld+json">\n{json.dumps(ld, ensure_ascii=False)}\n</script>\n'
                 f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}\n{LEAFLET_HEAD}')

        svc_photo = (
            f'<img class="content-photo" src="/images/bounce-houses/rainbow-castle-1.jpg" '
            f'alt="Classic castle bounce house set up for a birthday party in Atlanta, Georgia" '
            f'loading="lazy" width="1024" height="1024">'
        ) if slug == "classic-bounce-house-rentals" else featured_image_html(
            slug, alt_override=f"{s['name']} set up for an event in Atlanta, Georgia")

        page = head(f'{s["name"]} In Atlanta Georgia', s["intro"][:155].replace('"', "'"),
                    f"{DOMAIN}/services/{slug}/", extra)
        page += header("services") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/services/">Services</a> &rsaquo; {s["name"]}</div>
    <h1>{s["h1"]}</h1>
    <p>{s["intro"]}</p>
  </div>
</div>

<section id="map" class="alt">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Explore the Map</div>
      <h2>{s["name"]} Providers Near You</h2>
      <p>Browse {len(offering)} Atlanta providers offering {nml}. Click a listing or map pin to see details, ratings and reviews.</p>
    </div>
    {searchmap_html(area="Atlanta", zoom=10, service=SERVICES_SHORT[slug])}
  </div>
</section>

<section>
  <div class="container">
    <div class="grid" style="grid-template-columns:1.6fr 1fr; gap:48px; align-items:start;">
      <div class="content">
        <h2>About {s["name"]} in Atlanta</h2>
        {svc_photo}
        {body}

        <div class="callout">
          <p><strong>Serving all of metro Atlanta.</strong> Providers in our directory deliver {s["name"].lower()} to Atlanta, Buckhead, Midtown, Decatur, Sandy Springs, Marietta, Roswell, East Point and surrounding Georgia communities.</p>
        </div>

        <h2>{s["name"]} Price Estimates in Atlanta</h2>
        <p>Below are typical Atlanta price ranges for {s["name"].lower()} by event size. Final pricing depends on the date, delivery distance, rental duration and add-ons. Request a free quote for an exact figure.</p>
        <div class="price-grid">
          {prices}
        </div>

        <h2>Atlanta Providers Offering {s["name"]}</h2>
        <p>The following directory providers handle {s["name"].lower()} in the Atlanta area. Select a provider to view full details and reviews:</p>
        <ul class="bullet-services">
            {providers_links}
        </ul>

        <h2>{s["name"]} by Atlanta Area</h2>
        <p>We connect you with providers offering {s["name"].lower()} across the metro:</p>
        <ul class="bullet-services">
            {loc_links}
            <li><a href="/locations/">View all service areas</a></li>
        </ul>

        <h2>Other Bounce House Rental Services in Atlanta</h2>
        <ul>
            {others}
        </ul>
      </div>

      <aside>
        <div class="quote-card" style="position:sticky; top:90px;">
          <h2>Book {s["name"]}</h2>
          <p class="sub">Tell us about your event and we'll match you with available Atlanta providers in minutes.</p>
          <a class="btn btn-block" href="#" data-wizard-open>Book Now &rsaquo;</a>
          <div class="hero-trust" style="margin-top:14px;justify-content:center;">
            <span>Free quotes</span>
            <span>No obligation</span>
            <span>Fast response</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Book {s["name"]} in Atlanta Today</h2>
    <p>Tell us about your event and we'll match you with available Atlanta providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
</body>
</html>
'''
        d = os.path.join(ROOT, "services", slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(page)


# ----------------------------------------------------------------- specialty service sub-pages
def build_specialty_service_pages():
    SPECIALTY_PAGES = [
        {
            "slug": "chiavari-chair-rentals",
            "name": "Chiavari Chair Rentals Atlanta",
            "h1": "Chiavari Chair Rentals in Atlanta Georgia",
            "meta_desc": "Chiavari chair rentals in Atlanta, Georgia for weddings, galas and corporate events. Compare local providers, view pricing and get a free quote. Call (401) 889-0182.",
            "intro": "Chiavari chair rentals in Atlanta, Georgia are the gold standard for elegant event seating. These lightweight, stackable resin and wood chairs are a fixture at Atlanta weddings, fundraising galas and corporate awards dinners.",
            "body": [
                "Chiavari chairs originated in Chiavari, Italy and have become the most requested formal chair rental in Atlanta. Available in gold, silver, white, black and mahogany finishes, they pair with almost any linen color and event theme. Their slim profile allows more seating per square foot than traditional banquet chairs, making them ideal for Atlanta ballrooms, estate gardens and tent events.",
                "Atlanta rental providers typically include cushions in ivory, black or champagne at no extra charge with chiavari chair orders. Minimum order quantities start around 50 chairs for most providers, with delivery, setup and pickup included in the quoted price. Book 4 to 6 weeks ahead for spring wedding season when demand peaks across the metro."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Small Event", "amount": "$4&ndash;$7", "sub": "/ chair (min 50)", "items": ["Gold, silver or white finish", "Cushion included", "Delivery within Atlanta", "Setup and pickup"]},
                {"tier": "Medium Event", "amount": "$3.50&ndash;$5.50", "sub": "/ chair (100+ chairs)", "items": ["Any finish color", "Cushion choice included", "Metro Atlanta delivery", "Full setup service"]},
                {"tier": "Large Event", "amount": "$2.50&ndash;$4", "sub": "/ chair (200+ chairs)", "items": ["Volume discount rate", "Multiple finishes available", "Extended delivery radius", "Dedicated setup crew"]},
            ],
            "faqs": [
                ("How much do chiavari chair rentals cost in Atlanta?", "In Atlanta, chiavari chairs typically rent for $3.50 to $7 per chair depending on quantity and finish. Most providers include cushions and delivery within the metro. Request a free quote for exact pricing on your order size."),
                ("What finishes are available for chiavari chairs in Atlanta?", "Atlanta rental providers stock chiavari chairs in gold, silver, white, black and natural wood (mahogany) finishes. Gold and white are the most popular for weddings, while black suits corporate galas."),
                ("Do chiavari chair rentals include cushions?", "Most Atlanta providers include standard cushions — ivory, black or champagne — with chiavari chair orders at no additional cost. Premium or custom cushion colors may carry a small surcharge."),
            ],
        },
        {
            "slug": "ghost-chair-rentals",
            "name": "Ghost Chair Rentals Atlanta",
            "h1": "Ghost Chair Rentals in Atlanta Georgia",
            "meta_desc": "Ghost chair rentals in Atlanta, Georgia for modern weddings and corporate events. Clear acrylic Philippe Starck-style chairs. Compare providers and get a free quote.",
            "intro": "Ghost chair rentals in Atlanta, Georgia bring a modern, transparent elegance to weddings, product launches and rooftop events. These clear acrylic Philippe Starck-inspired chairs are one of the most requested contemporary seating options in the metro.",
            "body": [
                "Ghost chairs are made from a single piece of injection-molded polycarbonate, making them incredibly durable yet visually weightless. Their clear profile lets floral centerpieces and table linens take center stage without visual clutter, which is why Atlanta event designers frequently specify them for minimalist and glam wedding styles. They work equally well indoors at hotel ballrooms and outdoors on patios or under frame tents.",
                "Atlanta ghost chair rentals are available in clear, smoke gray and colored tinted versions from select providers. Because they stack efficiently, large orders are easy to transport and set up quickly. Most providers deliver, arrange and collect ghost chairs as part of a full decor rental package alongside farm tables, cocktail tables or chiavari chairs for mixed seating configurations."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Small Event", "amount": "$5&ndash;$9", "sub": "/ chair (min 25)", "items": ["Clear polycarbonate", "Delivery within Atlanta", "Setup and pickup", "Pairs with any table style"]},
                {"tier": "Medium Event", "amount": "$4&ndash;$7", "sub": "/ chair (75+ chairs)", "items": ["Clear or tinted finish", "Metro Atlanta delivery", "Full setup service", "Available in mixed styles"]},
                {"tier": "Large Event", "amount": "$3&ndash;$5.50", "sub": "/ chair (150+ chairs)", "items": ["Volume discount pricing", "Extended delivery radius", "Dedicated setup crew", "Coordinated with table rentals"]},
            ],
            "faqs": [
                ("How much do ghost chair rentals cost in Atlanta?", "Ghost chairs in Atlanta typically rent for $3 to $9 per chair depending on quantity. Clear polycarbonate ghost chairs are the most common. Delivery and setup are usually included within the metro. Request a free quote for your event count."),
                ("Are ghost chairs suitable for outdoor Atlanta events?", "Yes. Polycarbonate ghost chairs are weather-resistant and suitable for outdoor events under tents or on patios. They are UV-stable and will not crack in Georgia's heat. Always confirm with the provider for extreme weather conditions."),
                ("Can ghost chairs be mixed with other chair styles?", "Absolutely. Many Atlanta event designers mix ghost chairs with chiavari chairs or farm benches for visual contrast. Providers can accommodate mixed orders across multiple chair styles in a single delivery."),
            ],
        },
        {
            "slug": "kids-table-and-chair-rentals",
            "name": "Kids Table and Chair Rentals Atlanta",
            "h1": "Kids Table and Chair Rentals in Atlanta Georgia",
            "meta_desc": "Kids table and chair rentals in Atlanta, Georgia for birthday parties, school events and family gatherings. Child-sized folding tables and chairs delivered and set up.",
            "intro": "Kids table and chair rentals in Atlanta, Georgia provide the right-sized seating for children at birthday parties, school events, family reunions and church gatherings. Child-height folding tables and chairs keep little guests comfortable and safe throughout the event.",
            "body": [
                "Standard kids tables measure approximately 4 feet long and 18 to 22 inches tall, paired with 12-inch to 14-inch high plastic or folding chairs designed for children up to around age 10. Atlanta providers offer round and rectangular kids tables, and sets typically come in packages of one table with four to six chairs so it is easy to order exactly the seating your guest count requires.",
                "Kids table and chair sets are a staple add-on alongside bounce house and inflatable rentals across Atlanta. Most providers deliver them as part of a combined rental order, and setup takes just a few minutes. They are lightweight, easy to wipe clean and available in white or natural plastic finishes that work with any party theme."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Small Set", "amount": "$25&ndash;$45", "sub": "/ table + 4 chairs", "items": ["One 4ft kids table", "4 child-height chairs", "Delivery within Atlanta", "Setup included"]},
                {"tier": "Medium Set", "amount": "$80&ndash;$140", "sub": "/ 3 tables + 18 chairs", "items": ["Three kids tables", "18 child-height chairs", "Metro Atlanta delivery", "Full setup service"]},
                {"tier": "Large Set", "amount": "$160&ndash;$280+", "sub": "/ 6+ tables + 36+ chairs", "items": ["Six or more kids tables", "36+ child-height chairs", "Extended delivery radius", "Fast setup crew"]},
            ],
            "faqs": [
                ("What size are kids rental tables and chairs in Atlanta?", "Kids rental tables are typically 4 feet long and 18 to 22 inches tall. Chairs are 12 to 14 inches high, suitable for children roughly ages 2 to 10. Ask your provider about age range recommendations for your guest mix."),
                ("Can I add kids tables to a bounce house rental order?", "Yes. Most Atlanta providers that rent bounce houses also offer kids tables and chairs as an add-on to a single delivery. Bundling saves on delivery fees and simplifies setup."),
                ("How many kids fit at one rental table?", "A standard 4-foot kids table comfortably seats 4 to 6 children. For a party of 20 kids, plan for 4 to 5 tables depending on spacing and the table style you choose."),
            ],
        },
        {
            "slug": "farmhouse-table-rentals",
            "name": "Farmhouse Table Rentals Atlanta",
            "h1": "Farmhouse Table Rentals in Atlanta Georgia",
            "meta_desc": "Farmhouse table rentals in Atlanta, Georgia for weddings, outdoor receptions and rustic events. Compare wood farm table providers, view pricing and get a free quote.",
            "intro": "Farmhouse table rentals in Atlanta, Georgia are the centerpiece of rustic, boho and outdoor wedding receptions. These solid wood harvest-style tables create a warm, communal dining atmosphere that is increasingly popular at Atlanta venue farms, estate gardens and park events.",
            "body": [
                "Farmhouse tables, also called harvest tables or farm tables, are typically made from reclaimed or stained wood planks on a sturdy trestle base. Standard sizes are 8 feet long and seat 8 to 10 guests per table. Because they have a naturally beautiful wood surface, they are often used without tablecloths, lowering linen costs while maintaining an upscale look. Ghost chairs, cross-back chairs or benches are popular companions to farmhouse tables at Atlanta events.",
                "Atlanta farmhouse table providers deliver, arrange and collect tables as part of a full furniture rental package. Many providers offer matching benches and cross-back or chiavari chairs for a cohesive look. Book farmhouse tables early in spring wedding season, as inventory sells out quickly at Atlanta's premier wedding venues including The Farm at High Shoals, Summerour Studio and Ponce City Market event spaces."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Small Event", "amount": "$80&ndash;$130", "sub": "/ table", "items": ["One 8ft farmhouse table", "Seats 8&ndash;10 guests", "Delivery within Atlanta", "Setup and pickup"]},
                {"tier": "Medium Event", "amount": "$65&ndash;$110", "sub": "/ table (5+ tables)", "items": ["5 or more tables", "Volume discount rate", "Metro Atlanta delivery", "Coordinated chair pairing"]},
                {"tier": "Large Event", "amount": "$55&ndash;$90", "sub": "/ table (10+ tables)", "items": ["10+ tables", "Extended delivery radius", "Full setup crew", "Matching bench and chair options"]},
            ],
            "faqs": [
                ("How much do farmhouse table rentals cost in Atlanta?", "Farmhouse tables in Atlanta rent for approximately $55 to $130 per table depending on quantity and provider. Most include delivery and setup within the metro area. Request a free quote for your event size."),
                ("What chairs go best with farmhouse table rentals?", "Cross-back chairs, ghost chairs, chiavari chairs and matching wooden benches all pair beautifully with farmhouse tables. Many Atlanta providers offer bundled pricing when you rent chairs and tables together."),
                ("Are tablecloths needed for farmhouse table rentals?", "Most clients choose to leave farmhouse tables bare or add simple burlap or linen runners to showcase the wood grain. Full tablecloths are optional and available from most Atlanta providers as a linen add-on."),
            ],
        },
        {
            "slug": "throne-chair-rentals",
            "name": "Throne Chair Rentals Atlanta",
            "h1": "Throne Chair Rentals in Atlanta Georgia",
            "meta_desc": "Throne chair rentals in Atlanta, Georgia for weddings, sweet 16s and VIP events. Gold, white and black sweetheart throne chairs. Get a free quote today.",
            "intro": "Throne chair rentals in Atlanta, Georgia give the guest of honor a show-stopping seat at weddings, sweet 16 parties, baby showers and quinceañeras. These large, ornate sweetheart chairs are one of the most requested accent rentals for VIP photo moments across the Atlanta metro.",
            "body": [
                "Throne chairs are oversized upholstered chairs with high backs, typically finished in gold-leaf, white or black lacquer with plush velvet or tufted cushioning. A single throne or a matching his-and-hers pair is set up at the sweetheart table or head of the room to create a focal point for photos and video. Atlanta providers offer gold baroque, all-white modern and blush-tufted styles to fit a wide range of wedding themes.",
                "Throne chair rentals in Atlanta are often paired with a matching throne table, love seat backdrop or floral arch. Most providers offer same-day setup and will coordinate placement with your venue coordinator. Because inventory is limited, book throne chairs 4 to 8 weeks in advance, especially for Saturday events during Atlanta's peak wedding season from April through October."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Single Throne", "amount": "$120&ndash;$200", "sub": "/ chair", "items": ["One throne chair", "Gold, white or black finish", "Delivery within Atlanta", "Placement and pickup"]},
                {"tier": "His & Hers Pair", "amount": "$200&ndash;$350", "sub": "/ pair", "items": ["Matching pair of thrones", "Coordinated style and finish", "Metro Atlanta delivery", "Sweetheart table setup"]},
                {"tier": "VIP Package", "amount": "$350&ndash;$600+", "sub": "/ package", "items": ["Throne pair + backdrop", "Coordinated decor elements", "Extended delivery radius", "Full setup and styling"]},
            ],
            "faqs": [
                ("How much does throne chair rental cost in Atlanta?", "Throne chairs in Atlanta rent for $120 to $200 each or $200 to $350 for a his-and-hers pair. Full VIP packages including backdrop and decor run $350 to $600+. Delivery is typically included within metro Atlanta."),
                ("What events are throne chairs used for in Atlanta?", "Throne chairs are popular for Atlanta weddings (as sweetheart chairs), sweet 16 parties, quinceañeras, baby showers and corporate VIP seating arrangements. They create a striking focal point for photos and video."),
                ("How far in advance should I book a throne chair rental?", "Book throne chairs 4 to 8 weeks ahead for spring and fall wedding season. Saturday dates in April, May, September and October fill fastest. Call (401) 889-0182 to check current availability."),
            ],
        },
        {
            "slug": "cocktail-table-rentals",
            "name": "Cocktail Table Rentals Atlanta",
            "h1": "Cocktail Table Rentals in Atlanta Georgia",
            "meta_desc": "Cocktail table rentals in Atlanta, Georgia for receptions, corporate events and parties. High-top round tables with or without linens. Compare providers and get a free quote.",
            "intro": "Cocktail table rentals in Atlanta, Georgia are a must-have for receptions, networking events and outdoor parties. These round high-top tables encourage guests to mingle and are easy to dress with spandex covers, full-length linens or simple table runners.",
            "body": [
                "Cocktail tables, also called high-top or bistro tables, measure approximately 30 inches in diameter and stand 42 inches tall. They seat 3 to 4 guests standing or with bar stools, and they are a versatile solution for cocktail hours, buffet perimeters, bar setups and outdoor reception areas. Atlanta providers stock both standard metal-frame folding cocktail tables and premium wood-top versions for a more polished look.",
                "Spandex stretch covers in white, black, ivory and dozens of colors are available from most Atlanta rental providers to dress cocktail tables cleanly without visible hardware. Full-length overlay linens create a more formal presentation. Most providers include delivery, setup and pickup within the metro area, and cocktail tables can be bundled with chairs, tents and other furniture in a single order for easy event planning."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Small Order", "amount": "$12&ndash;$22", "sub": "/ table", "items": ["One cocktail table", "With or without linen", "Delivery within Atlanta", "Setup and pickup"]},
                {"tier": "Medium Order", "amount": "$10&ndash;$18", "sub": "/ table (5+ tables)", "items": ["5 or more cocktail tables", "Linen options available", "Metro Atlanta delivery", "Bundled with chair orders"]},
                {"tier": "Large Order", "amount": "$8&ndash;$15", "sub": "/ table (10+ tables)", "items": ["Volume discount rate", "Full linen dressing available", "Extended delivery radius", "Coordinated with full furniture package"]},
            ],
            "faqs": [
                ("How much do cocktail table rentals cost in Atlanta?", "Cocktail tables in Atlanta rent for $8 to $22 per table depending on quantity. Spandex covers or linens add $4 to $12 per table. Delivery within metro Atlanta is typically included. Request a free quote for your event."),
                ("Do cocktail table rentals include linens?", "Linens are usually offered as an add-on. Spandex stretch covers are the most popular choice for cocktail tables and are available in dozens of colors. Full-length round linens create a more formal look."),
                ("How many cocktail tables do I need for my event?", "A general guide is one cocktail table per 6 to 8 standing guests for a cocktail-style reception. For a 100-person event with a mix of seated and standing areas, plan for 8 to 12 cocktail tables alongside your seated dinner tables."),
            ],
        },
        {
            "slug": "slushy-machine-rentals",
            "name": "Slushy Machine Rentals Atlanta",
            "h1": "Slushy Machine and Snow Cone Rentals in Atlanta Georgia",
            "meta_desc": "Slushy machine and snow cone rentals in Atlanta, Georgia for outdoor parties, school events and corporate picnics. Frozen drink machines with supplies included. Free quote.",
            "intro": "Slushy machine and snow cone rentals in Atlanta, Georgia are a summer party staple. Frozen drink machines keep guests cool during hot Georgia outdoor events and are a hit with guests of all ages at birthday parties, school field days, church festivals and corporate picnics.",
            "body": [
                "Slushy machines and snow cone makers produce frozen treats using either a rotating drum freeze system (for slushies and margaritas) or a block-ice shaving blade (for traditional snow cones). Atlanta providers supply the machine along with enough flavored syrups, cups and spoons to serve your guest count. Popular flavors include cherry, blue raspberry, watermelon, mango and lemon-lime. Non-alcoholic options are standard; providers can also supply a frozen margarita machine for adult events.",
                "Slushy and snow cone machine rentals run on a standard 110V household outlet and require a nearby power source. Most Atlanta providers include delivery, setup and a usage walkthrough in the rental price. Machines can serve 75 to 200+ guests per event depending on capacity. Bundle a slushy machine with a bounce house or other inflatable for a complete summer party package at a discounted combined rate."
            ],
            "parent_slug": "concession-rentals",
            "parent_name": "Concession Rentals",
            "price_tiers": [
                {"tier": "Small Event", "amount": "$75&ndash;$120", "sub": "/ machine", "items": ["One slushy or snow cone machine", "Supplies for 75 servings", "4-hour rental window", "Delivery within Atlanta"]},
                {"tier": "Medium Event", "amount": "$130&ndash;$200", "sub": "/ event", "items": ["Large-capacity machine", "Supplies for 150 servings", "6-hour rental window", "Metro Atlanta delivery"]},
                {"tier": "Large Event", "amount": "$220&ndash;$400+", "sub": "/ event", "items": ["Two machines or high-capacity unit", "Supplies for 300+ servings", "Full-day rental", "Extended Atlanta radius"]},
            ],
            "faqs": [
                ("How much does a slushy machine rental cost in Atlanta?", "Slushy and snow cone machine rentals in Atlanta typically cost $75 to $200 per machine per event, including supplies for 75 to 150 servings. Larger capacity setups or two-machine orders run $220 to $400+. Delivery is usually included within metro Atlanta."),
                ("What flavors come with a slushy machine rental in Atlanta?", "Most Atlanta providers include a selection of standard flavors such as cherry, blue raspberry, watermelon, lemon-lime and mango. Some providers offer premium or custom flavor options for an additional charge."),
                ("Can I use a slushy machine for alcoholic frozen drinks?", "Yes. Some Atlanta providers offer a frozen margarita or daiquiri machine for adult events. Confirm with your provider that this option is available and legal for your venue type before booking."),
            ],
        },
    ]

    all_specialty_slugs = [p["slug"] for p in SPECIALTY_PAGES]

    for pg in SPECIALTY_PAGES:
        slug = pg["slug"]
        cross_links = "\n            ".join(
            f'<li><a href="/services/{s}/">{n}</a></li>'
            for s, n in SPECIALTY_SLUGS if s != slug)

        prices_html = "\n          ".join(
            f'''<div class="price-card{" featured" if i == 1 else ""}">
            <div class="tier">{pt["tier"]}</div>
            <div class="amount">{pt["amount"]} <span>{pt["sub"]}</span></div>
            <ul>
              {"".join(f"<li>{item}</li>" for item in pt["items"])}
            </ul>
          </div>''' for i, pt in enumerate(pg["price_tiers"]))

        body_html = "\n        ".join(f"<p>{p}</p>" for p in pg["body"])

        faq_tuples = [(q, f"<p>{a}</p>") for q, a in pg["faqs"]]
        faq_html, faq_ld = faq_block(faq_tuples)

        bc_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Services", "item": DOMAIN + "/services/"},
            {"@type": "ListItem", "position": 3, "name": pg["parent_name"], "item": f"{DOMAIN}/services/{pg['parent_slug']}/"},
            {"@type": "ListItem", "position": 4, "name": pg["name"], "item": f"{DOMAIN}/services/{slug}/"},
        ]}
        svc_ld = {"@context": "https://schema.org", "@type": "Service",
                  "serviceType": pg["name"],
                  "areaServed": {"@type": "City", "name": "Atlanta"},
                  "provider": {"@type": "LocalBusiness", "name": "Atlanta Bounce House Rental Directory", "telephone": PHONE_HREF},
                  "url": f"{DOMAIN}/services/{slug}/"}
        extra = (f'<script type="application/ld+json">\n{json.dumps(bc_ld, ensure_ascii=False)}\n</script>\n'
                 f'<script type="application/ld+json">\n{json.dumps(svc_ld, ensure_ascii=False)}\n</script>\n{faq_ld}')

        page = head(pg["name"], pg["meta_desc"], f"{DOMAIN}/services/{slug}/", extra)
        page += header("services") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/services/">Services</a> &rsaquo; <a href="/services/{pg["parent_slug"]}/">{pg["parent_name"]}</a> &rsaquo; {pg["name"]}</div>
    <h1>{pg["h1"]}</h1>
    <p>{pg["intro"]}</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="grid" style="grid-template-columns:1.6fr 1fr; gap:48px; align-items:start;">
      <div class="content">
        <h2>About {pg["name"]} in Atlanta</h2>
        {featured_image_html(slug, alt_override=f'{pg["name"]} set up for an event in Atlanta, Georgia')}
        {body_html}

        <div class="callout">
          <p><strong>Serving all of metro Atlanta.</strong> Providers in our directory deliver {pg["name"].lower()} to Atlanta, Buckhead, Midtown, Decatur, Sandy Springs, Marietta, Roswell and surrounding Georgia communities.</p>
        </div>

        <h2>{pg["name"]} Price Estimates in Atlanta</h2>
        <p>Below are typical Atlanta price ranges. Final pricing depends on the date, delivery distance, rental duration and add-ons. Request a free quote for an exact figure.</p>
        <div class="price-grid">
          {prices_html}
        </div>

        <h2>Parent Service: {pg["parent_name"]}</h2>
        <p>For a broader selection of chairs, tables and seating, see the full <a href="/services/{pg["parent_slug"]}/">{pg["parent_name"]} in Atlanta</a> page, or browse our <a href="/locations/">Atlanta service areas</a> to find providers near you.</p>

        <h2>Other Specialty Equipment Pages</h2>
        <ul>
            {cross_links}
        </ul>
      </div>

      <aside>
        <div class="quote-card" style="position:sticky; top:90px;">
          <h2>Book {pg["name"]}</h2>
          <p class="sub">Tell us about your event and we'll match you with available Atlanta providers in minutes.</p>
          <a class="btn btn-block" href="#" data-wizard-open>Book Now &rsaquo;</a>
          <div class="hero-trust" style="margin-top:14px;justify-content:center;">
            <span>Free quotes</span>
            <span>No obligation</span>
            <span>Fast response</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Book {pg["name"]} in Atlanta Today</h2>
    <p>Tell us about your event and we'll match you with available Atlanta providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        d = os.path.join(ROOT, "services", slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(page)


# ----------------------------------------------------------------- bounce houses
def build_bounce_houses():
    items = json.load(open(os.path.join(ROOT, "data", "bounce-houses.json")))

    # --- index page ---
    cards = []
    for it in items:
        from_price = it["pricing"][0]["price"]
        has_img = True  # placeholder toggle; real check would test file existence
        img_html = (f'<img class="bh-card-img" src="{it["images"][0]}" alt="{esc(it["name"])} rental in Atlanta, Georgia" loading="lazy" width="600" height="450">'
                    if has_img else
                    f'<div class="bh-card-img-placeholder">Image coming soon</div>')
        cards.append(f'''    <a class="bh-card" href="/bounce-houses/{it["slug"]}/">
      {img_html}
      <div class="bh-card-body">
        <div class="bh-cat">{esc(it["category"])}</div>
        <h3>{esc(it["name"])}</h3>
        <p class="bh-from">From <strong>${from_price}</strong> &middot; Setup &amp; teardown included</p>
      </div>
    </a>''')
    cards_html = "\n".join(cards)

    idx = head(
        "Bounce Houses for Rent in Atlanta Georgia | ATL Bounce House Rentals",
        "Browse bounce houses available for rent across Atlanta, Georgia. Classic castles, rainbow combos and more — setup and teardown included. Call (401) 889-0182 for pricing and availability.",
        DOMAIN + "/bounce-houses/")
    idx += header("bounce-houses") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Bounce Houses</div>
    <h1>Bounce Houses for Rent in Atlanta, Georgia</h1>
    <p>Browse our selection of inflatable bounce houses available for rent across Atlanta and the surrounding metro. All units include delivery, setup and teardown. Call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> or request a quote below for pricing and availability.</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="bh-grid">
{cards_html}
    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Need Help Choosing the Right Bounce House?</h2>
    <p>Tell us about your event — guest count, date, venue — and we'll match you with the perfect unit and best price.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "bounce-houses")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(idx)

    # --- detail pages ---
    for it in items:
        pricing_rows = []
        for tier in it["pricing"]:
            featured_cls = " featured" if tier["featured"] else ""
            pricing_rows.append(f'''          <div class="bh-tier{featured_cls}">
            <div class="bh-tier-label">{esc(tier["tier"])}<small>{esc(tier["label"])}</small></div>
            <div class="bh-tier-price">${esc(tier["price"])}</div>
          </div>''')
        pricing_html = "\n".join(pricing_rows)

        included_html = "\n".join(f"<li>{esc(i)}</li>" for i in it["included"])
        you_need_html = "\n".join(f"<li>{esc(i)}</li>" for i in it["you_need"])
        policies_html = "\n".join(f"<li>{esc(p)}</li>" for p in it["policies"])

        imgs = it.get("images", [])
        gallery_html = "\n".join(
            f'<img src="{esc(src)}" alt="{esc(it["name"])} rental in Atlanta, Georgia' +
            (' — product view' if i == 0 else ' set up for a backyard party') + '" loading="lazy">'
            for i, src in enumerate(imgs)
        ) if imgs else f'<div class="bh-gallery-placeholder">Photos coming soon — call {PHONE_DISPLAY} to see more.</div>'

        ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": it["name"],
            "description": it["tagline"],
            "image": [DOMAIN + src for src in imgs],
            "brand": {"@type": "Brand", "name": "Atlanta Bounce House Rentals"},
            "offers": {
                "@type": "Offer",
                "priceCurrency": "USD",
                "price": it["pricing"][0]["price"],
                "availability": "https://schema.org/InStock",
                "seller": {"@type": "Organization", "name": "Atlanta Bounce House Rentals", "telephone": PHONE_HREF}
            }
        }, ensure_ascii=False)

        extra = f'<script type="application/ld+json">\n{ld}\n</script>'

        page = head(
            f'{it["name"]} Rental Atlanta Georgia | ATL Bounce House Rentals',
            f'Rent the {it["name"]} in Atlanta, Georgia. {it["tagline"]} Starting at ${it["pricing"][0]["price"]}. Call (401) 889-0182 or request a quote.',
            f'{DOMAIN}/bounce-houses/{it["slug"]}/',
            extra)
        page += header("bounce-houses") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/bounce-houses/">Bounce Houses</a> &rsaquo; {esc(it["name"])}</div>
    <h1>{esc(it["name"])} Rental</h1>
    <p>{esc(it["tagline"])}</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="bh-detail">

      <!-- Left: gallery + specs -->
      <div>
        <div class="bh-gallery">
          {gallery_html}
        </div>

        <h2 style="margin-top:34px;">Product Details</h2>

        <dl class="bh-specs" style="margin-bottom:28px;">
          <div class="bh-spec"><dt>Item Dimensions</dt><dd>{esc(it["dimensions_item"])}</dd></div>
          <div class="bh-spec"><dt>Space Needed</dt><dd>{esc(it["dimensions_space"])}</dd></div>
          <div class="bh-spec"><dt>Circuits</dt><dd>{it["circuits"]}</dd></div>
          <div class="bh-spec"><dt>Max Occupancy</dt><dd>{esc(it["max_occupancy"])}</dd></div>
        </dl>

        <h3>What&rsquo;s Included</h3>
        <ul class="bh-policy-list" style="margin-bottom:24px;">
          {included_html}
        </ul>

        <h3>What You&rsquo;ll Need</h3>
        <ul class="bh-policy-list" style="margin-bottom:24px;">
          {you_need_html}
        </ul>

        <h3>Policies &amp; Notes</h3>
        <ul class="bh-policy-list">
          {policies_html}
        </ul>
      </div>

      <!-- Right: pricing + contact -->
      <div class="bh-info">
        <div class="bh-pricing-card">
          <h3>Pricing</h3>
{pricing_html}
          <ul class="bh-inclusions">
            <li>All prices include setup and teardown</li>
            <li>Reserve with just a ${it["deposit"]} deposit</li>
            <li>{it["extra_per_hour_pct"]}% extra per additional hour</li>
          </ul>
        </div>

        <div class="bh-contact-card">
          <h3>Get Pricing &amp; Reserve</h3>
          <p class="sub">Tell us about your event and we&rsquo;ll confirm availability and send you a quote in minutes.</p>
          <a class="btn btn-block" href="#" data-wizard-open style="margin-bottom:14px;">Book Now &rsaquo;</a>
          <div class="bh-or">— or fill out the form —</div>
          <form data-quote-form novalidate>
            <div data-success class="form-success" style="display:none;">
              Thanks! We received your request for the {esc(it["name"])}. We&rsquo;ll be in touch shortly. Need it sooner? Call <strong>{PHONE_DISPLAY}</strong>.
            </div>
            <div data-fields>
              <div class="field"><label for="q-name">Full Name</label><input id="q-name" name="name" type="text" required></div>
              <div class="field"><label for="q-phone">Phone</label><input id="q-phone" name="phone" type="tel" required></div>
              <div class="field"><label for="q-email">Email</label><input id="q-email" name="email" type="email" required></div>
              <input type="hidden" name="item" value="{esc(it["name"])}">
              <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div><label for="q-date">Event Date</label><input id="q-date" name="event_date" type="date"></div>
                <div><label for="q-zip">ZIP Code</label><input id="q-zip" name="zip" type="text" placeholder="30303"></div>
              </div>
              <div class="field"><label for="q-msg">Message (optional)</label><textarea id="q-msg" name="message" rows="3" placeholder="Any questions or details about your event..."></textarea></div>
              <button class="btn btn-block" type="submit">Request a Quote</button>
            </div>
          </form>
        </div>
      </div>

    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Ready to Book?</h2>
    <p>Tell us about your event and we'll confirm availability and lock in your date. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        slug_dir = os.path.join(ROOT, "bounce-houses", it["slug"])
        os.makedirs(slug_dir, exist_ok=True)
        open(os.path.join(slug_dir, "index.html"), "w").write(page)
def build_locations(providers):
    """Service-area landing pages: /locations/ index + one page per metro city/district.
    Every page links up to the index, across to nearby areas, down to services and
    matched providers, and out to the cheap-rentals page — so none are orphaned."""

    # --- index page ---
    # Cities with actual matched listings have been migrated to full
    # programmatic /find/ pages; only list the remaining cities here.
    remaining_locs = [loc for loc in LOCATIONS if loc["slug"] not in MIGRATED_LOCATION_SLUGS]
    migrated_locs = [loc for loc in LOCATIONS if loc["slug"] in MIGRATED_LOCATION_SLUGS]

    cards = []
    for loc in remaining_locs:
        n = providers_for_location(loc, providers)
        hoods = ", ".join(loc["neighborhoods"][:3])
        cards.append(f'''    <a class="loc-card" href="/locations/{loc["slug"]}/">
      <h3>Bounce House Rentals in {esc(loc["name"])}</h3>
      <p class="loc-card-hoods">{esc(hoods)}</p>
      <p class="loc-card-meta">{len(n)} nearby provider{"s" if len(n) != 1 else ""} &middot; {esc(loc["type"].title())}</p>
    </a>''')
    cards_html = "\n".join(cards)
    svc_links = "\n      ".join(
        f'<li><a href="/services/{s}/">{SERVICES[s]} in Atlanta</a></li>' for s in SERVICES)

    migrated_links = "\n      ".join(
        f'<li><a href="{location_href(loc)}">Bounce House Rentals in {esc(loc["name"])}</a></li>'
        for loc in migrated_locs)
    migrated_html = ""
    if migrated_locs:
        migrated_html = f'''
<section>
  <div class="container content" style="max-width:none;">
    <h2>Cities With Local Listings</h2>
    <p>These cities have dedicated pages with local providers, an interactive map and pricing on our <a href="/find/">Find hub</a>:</p>
    <ul class="bullet-services">
      {migrated_links}
    </ul>
  </div>
</section>'''

    item_ld = {"@context": "https://schema.org", "@type": "ItemList",
               "itemListElement": [
                   {"@type": "ListItem", "position": i + 1,
                    "name": f'Bounce House Rentals in {l["name"]}',
                    "url": f'{DOMAIN}{location_href(l)}'}
                   for i, l in enumerate(LOCATIONS)]}
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
        {"@type": "ListItem", "position": 2, "name": "Service Areas", "item": DOMAIN + "/locations/"}]}
    extra = (f'<script type="application/ld+json">\n{json.dumps(item_ld, ensure_ascii=False)}\n</script>\n'
             f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n')

    idx = head(
        "Bounce House Rental Service Areas in Atlanta, Georgia | Cities We Serve",
        "Bounce house rentals across metro Atlanta, GA — Buckhead, Midtown, Decatur, Sandy Springs, Marietta, Roswell, Alpharetta and more. Find providers serving your city and get a free quote.",
        DOMAIN + "/locations/", extra)
    idx += header("locations") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Service Areas</div>
    <h1>Bounce House Rental Service Areas Across Metro Atlanta</h1>
    <p>We connect you with bounce house and party rental providers in every corner of the Atlanta metro. Choose your city or neighborhood below to see local providers and pricing.</p>
  </div>
</div>

<section>
  <div class="container">
    {featured_image_html(alt_override="Bounce house and party rentals set up for an event across metro Atlanta")}
    <div class="loc-grid">
{cards_html}
    </div>
  </div>
</section>
{migrated_html}
<section class="alt">
  <div class="container content" style="max-width:none;">
    <h2>Every Rental Service, Available Across Atlanta</h2>
    <p>No matter which area you are in, our directory providers offer the full range of party rentals:</p>
    <ul class="bullet-services">
      {svc_links}
    </ul>
    <div class="callout">
      <p><strong>Looking for a deal?</strong> See our <a href="/cheap-bounce-house-rentals/">cheap bounce house rentals in Atlanta</a>, including $99 specials, or browse <a href="/bounce-houses/">bounce houses available to rent</a>.</p>
    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Find Bounce House Rentals Near You</h2>
    <p>Tell us about your event and we'll match you with local Atlanta providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "locations")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(idx)

    # --- individual city pages ---
    # Cities with matched listings are now full /find/ pages (see
    # build_find_pages); remove any stale build output and skip them here.
    for slug in MIGRATED_LOCATION_SLUGS:
        stale = os.path.join(ROOT, "locations", slug)
        if os.path.isdir(stale):
            shutil.rmtree(stale)

    for loc in remaining_locs:
        name = loc["name"]
        nl = name
        matched = providers_for_location(loc, providers)
        if matched:
            prov_links = "\n          ".join(
                f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>{prov_meta_html(p)}</li>'
                for p in matched)
            prov_intro = (f'These directory providers are based in or around {nl} and deliver across the area. '
                          f'Select a provider to view details, or call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> for a free quote:')
            prov_block = f'<ul class="bullet-services">\n          {prov_links}\n        </ul>'
        else:
            prov_intro = (f'Providers from across the Atlanta directory deliver to {nl}. '
                          f'Call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> or request a quote and we will match you with a company covering your ZIP code.')
            prov_block = (f'<p><a href="/partners.html">Browse all Atlanta providers</a> or '
                          f'<a href="/#providers">request a free quote</a> to be matched with one serving {nl}.</p>')

        svc_links_loc = "\n          ".join(
            f'<li><a href="/services/{s}/">{SERVICES[s]} in {nl}</a></li>' for s in SERVICES)
        hoods = ", ".join(loc["neighborhoods"])
        landmarks = ", ".join(loc["landmarks"])
        zips = ", ".join(loc["zips"])
        nearby = [LOC_BY_SLUG[s] for s in loc.get("nearby", []) if s in LOC_BY_SLUG]
        nearby_links = "\n          ".join(
            f'<li><a href="{location_href(x)}">Bounce House Rentals in {esc(x["name"])}</a></li>' for x in nearby)

        faqs = [
            (f"How much does it cost to rent a bounce house in {nl}?",
             f"<p>In {nl}, a classic bounce house typically rents for about $120&ndash;$260 per day, with combo slides, water slides and obstacle courses running roughly $180&ndash;$900+ depending on size. Final pricing depends on your date, delivery distance and rental length. <a href=\"/cheap-bounce-house-rentals/\">See current $99 specials</a> or <a href=\"/#providers\">request a free quote</a>.</p>"),
            (f"Do providers deliver bounce houses to {nl}?",
             f"<p>Yes. Directory providers deliver bounce houses, water slides, tents, tables, chairs and concessions throughout {nl}, including {esc(hoods)}, and handle setup and pickup.</p>"),
            (f"How far in advance should I book a bounce house in {nl}?",
             f"<p>For weekend dates in {nl} during Atlanta's busy spring and summer season, book 2&ndash;4 weeks ahead. Last-minute requests are welcome too&mdash;<a href=\"#\" data-wizard-open>book now</a> and we'll check live availability.</p>"),
            (f"What can I rent for a party in {nl}?",
             f"<p>You can rent classic bounce houses, bounce-and-slide combos, water slides, obstacle courses, concession machines, tents, tables and chairs, interactive games and complete party packages. See <a href=\"/services/\">all services</a>.</p>"),
        ]
        faq_html, faq_ld = faq_block(faqs)

        svc_ld = {"@context": "https://schema.org", "@type": "Service",
                  "serviceType": "Bounce House Rental",
                  "areaServed": {"@type": "Place", "name": f"{nl}, Georgia"},
                  "provider": {"@type": "LocalBusiness", "name": "Atlanta Bounce House Rental Directory",
                               "telephone": PHONE_HREF, "areaServed": f"{nl}, GA"},
                  "url": f"{DOMAIN}/locations/{loc['slug']}/"}
        bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Service Areas", "item": DOMAIN + "/locations/"},
            {"@type": "ListItem", "position": 3, "name": nl, "item": f"{DOMAIN}/locations/{loc['slug']}/"}]}
        extra = (f'<script type="application/ld+json">\n{json.dumps(svc_ld, ensure_ascii=False)}\n</script>\n'
                 f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}\n{LEAFLET_HEAD}')

        clat, clng = location_center(loc, providers)

        page = head(
            f"Bounce House Rentals in {nl}, GA | Atlanta Bounce House Rentals",
            f"Rent bounce houses, water slides and party rentals in {nl}, Georgia. Compare local providers serving {hoods[:80]}. Free quotes &mdash; call {PHONE_DISPLAY}.",
            f"{DOMAIN}/locations/{loc['slug']}/", extra)
        page += header("locations") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/locations/">Service Areas</a> &rsaquo; {esc(nl)}</div>
    <h1>Bounce House Rentals in {esc(nl)}, Georgia</h1>
    <p>{esc(loc["blurb"])}</p>
  </div>
</div>

<section class="alt" id="map">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Explore the Map</div>
      <h2>Bounce House Providers On the Map Near {esc(nl)}</h2>
      <p>Browse party rental providers closest to {esc(nl)}. Click a listing or map pin to see details, ratings and reviews.</p>
    </div>
    {searchmap_html(area=nl, lat=clat, lng=clng, zoom=11)}
  </div>
</section>

<section>
  <div class="container">
    <div class="grid" style="grid-template-columns:1.6fr 1fr; gap:48px; align-items:start;">
      <div class="content">
        <h2>Bounce House &amp; Party Rentals Serving {esc(nl)}</h2>
        <img class="content-photo" src="/images/hero-bounce-house.jpg" alt="Bounce house and slide combo set up for a birthday party near {esc(nl)}, Georgia" loading="lazy" width="1376" height="768">
        <p>Whether you are planning a birthday party, school field day, church festival or corporate family day in {esc(nl)}, our directory connects you with vetted local providers. Popular areas served include {esc(hoods)}, with delivery near {esc(landmarks)} and throughout ZIP codes {esc(zips)}.</p>

        <div class="callout">
          <p><strong>Serving all of {esc(nl)} and nearby Atlanta.</strong> Providers deliver bounce houses, water slides, obstacle courses, tents, tables, chairs and concessions with setup and teardown included.</p>
        </div>

        <h2>Rental Services Available in {esc(nl)}</h2>
        <ul class="bullet-services">
          {svc_links_loc}
        </ul>

        <h2>Bounce House Providers Near {esc(nl)}</h2>
        <p>{prov_intro}</p>
        {prov_block}

        <h2>Looking for Cheap Bounce House Rentals in {esc(nl)}?</h2>
        <p>Compare budget-friendly options including $99 bounce house specials on our <a href="/cheap-bounce-house-rentals/">cheap bounce house rentals</a> page, or browse individual <a href="/bounce-houses/">bounce houses available to rent</a>.</p>

        <h2>Nearby Service Areas</h2>
        <ul>
          {nearby_links}
          <li><a href="/locations/">View all Atlanta service areas</a></li>
        </ul>
      </div>

      <aside>
        <div class="quote-card" style="position:sticky; top:90px;">
          <h2>Book Rentals in {esc(nl)}</h2>
          <p class="sub">Tell us about your event and we'll match you with available providers serving {esc(nl)} in minutes.</p>
          <a class="btn btn-block" href="#" data-wizard-open>Book Now &rsaquo;</a>
          <div class="hero-trust" style="margin-top:14px;justify-content:center;">
            <span>Free quotes</span>
            <span>No obligation</span>
            <span>Fast response</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Book a Bounce House in {esc(nl)} Today</h2>
    <p>Tell us about your event and we'll match you with available {esc(nl)} providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        sd = os.path.join(ROOT, "locations", loc["slug"])
        os.makedirs(sd, exist_ok=True)
        open(os.path.join(sd, "index.html"), "w").write(page)


# ----------------------------------------------------------------- /find/ programmatic hub
# Each entry defines one programmatic page family: a service paired with a URL
# prefix. A page is generated per city ONLY when that city has at least one
# matched provider (by ZIP) offering the service — no thin/empty pages.
FIND_PAGE_FAMILIES = [
    # match_mode "any": matched = every provider in the city by ZIP, regardless
    # of service (this is the full replacement for the old /locations/ pages).
    {"url_prefix": "bounce-house-rentals", "page_name": "Bounce House Rentals", "match_mode": "any"},
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "tents-table-chair-rentals"},
    {"service_slug": "photo-booth-rentals", "url_prefix": "photo-booth-rentals"},
    {"service_slug": "obstacle-course-rentals", "url_prefix": "obstacle-course-rentals"},
    {"service_slug": "water-slide-rentals", "url_prefix": "water-slide-rentals"},
    {"service_slug": "silent-disco-rentals", "url_prefix": "silent-disco-rentals"},
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "event-table-rentals", "page_name": "Event Table Rentals"},
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "event-chair-rentals", "page_name": "Event Chair Rentals"},
    {"service_slug": "classic-bounce-house-rentals", "url_prefix": "99-bounce-house-rentals", "page_name": "$99 Bounce House Rentals", "map_filter": "$99 Bounce House Rentals"},
    # match_mode "tag": matched by the finer-grained MAP_EXTRA_KEYWORDS tag
    # instead of a core SERVICES slug. service_slug is kept only so the page
    # can cross-link to the closest real /services/ page.
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "chair-rentals", "page_name": "Chair Rentals",
     "match_mode": "tag", "tag": "Chair Rentals"},
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "tent-rentals", "page_name": "Tent Rentals",
     "match_mode": "tag", "tag": "Tent Rentals"},
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "table-rentals", "page_name": "Table Rentals",
     "match_mode": "tag", "tag": "Table Rentals",
     "desc_template": "There {is_are} {n} {provider_word} for Table Rentals in {city}, Georgia. Book today!"},
    # Chiavari is a chair style, not a distinct category in the data — reuse
    # the same "Chair Rentals" tag match (any chair-rental provider) per
    # instruction, just with its own title/URL/description.
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "chiavari-chair-rentals", "page_name": "Chiavari Chair Rentals",
     "match_mode": "tag", "tag": "Chair Rentals",
     "desc_template": "There {is_are} {n} {provider_word} for Chiavari Chair Rentals in {city}, Georgia. Book today!"},
    # Folding chair is also a style, not a distinct category — same reuse of
    # the "Chair Rentals" tag match (any chair-rental provider) per instruction.
    {"service_slug": "tents-tables-and-chair-rentals", "url_prefix": "folding-chair-rentals", "page_name": "Folding Chair Rentals",
     "match_mode": "tag", "tag": "Chair Rentals",
     "desc_template": "There {is_are} {n} {provider_word} for Folding Chair Rentals in {city}, Georgia. Book today!"},
    # match_mode "theme": like "any" (every provider in the city by ZIP —
    # never zero for a matched city), but with its own generic themed copy
    # instead of the Bounce-House-specific /locations/ replacement content.
    # Bounce houses, tents/tables/chairs, entertainment & staff, decor and
    # party packages are all "closely tied" services for a Halloween event.
    {"url_prefix": "halloween-event-rentals", "page_name": "Halloween Event Rentals", "match_mode": "theme",
     "theme_blurb": "Planning a Halloween party, trunk-or-treat, corporate fall event or trick-or-treat block party in {city}? The local providers below offer bounce houses, tents, tables and chairs, entertainment and staff, decor and other rentals closely tied to Halloween events, including {hoods}.",
     "theme_note": "Providers deliver bounce houses (including Halloween and fall-themed inflatables where available), tents, tables, chairs, entertainment and staff, and decor with setup and teardown included."},
    {"url_prefix": "gender-reveal-party-event-rentals", "page_name": "Gender Reveal Party Event Rentals", "match_mode": "theme",
     "theme_blurb": "Planning a gender reveal party or baby shower in {city}? The local providers below offer tents, tables and chairs, photo booths, balloon and decor styling, entertainment and staff, and other rentals closely tied to gender reveal events, including {hoods}.",
     "theme_note": "Providers deliver tents, tables, chairs, photo booths, balloon and decor styling, and entertainment and staff with setup and teardown included."},
    {"url_prefix": "kids-party-rentals", "page_name": "Kids Party Rentals", "match_mode": "theme",
     "theme_blurb": "Planning a kids' birthday party, school event or family celebration in {city}? The local providers below offer bounce houses, water slides, tables and chairs, photo booths, concessions, entertainment and staff, and other rentals closely tied to kids' parties, including {hoods}.",
     "theme_note": "Providers deliver bounce houses, water slides, tables, chairs, concessions, photo booths, and entertainment and staff with setup and teardown included."},
    {"url_prefix": "back-to-school-party-rentals", "page_name": "Back To School Party Rentals", "match_mode": "theme",
     "theme_blurb": "Planning a back-to-school bash, first-day-of-school party, teacher appreciation event or school carnival in {city}? The local providers below offer bounce houses, tents, tables and chairs, concessions, interactive games, entertainment and staff, and other rentals closely tied to back-to-school events, including {hoods}.",
     "theme_note": "Providers deliver bounce houses, tents, tables, chairs, concessions, interactive games, and entertainment and staff with setup and teardown included."},
]

# Metro-wide "near me" pages: one per core service, not fanned out by city.
# Only generated when at least one provider anywhere offers that service.
# Value is (display name, URL prefix); prefix defaults to the service slug
# itself when not overridden here.
NEAR_ME_OVERRIDES = {
    "classic-bounce-house-rentals": ("Bounce House Rentals", "bounce-house-rentals"),
}


def _providers_for_location_service(loc, providers, service_slug, limit=50):
    zset = set(loc.get("zips", []))
    matched = [p for p in providers if str(p.get("postal") or "").strip() in zset and service_slug in p["services"]]
    matched.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
    return matched[:limit]


def _providers_for_location_tag(loc, providers, tag, limit=50):
    zset = set(loc.get("zips", []))
    matched = [p for p in providers if str(p.get("postal") or "").strip() in zset and tag in extra_map_tags(p)]
    matched.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
    return matched[:limit]


def build_find_pages(providers):
    """/find/ hub + one programmatic landing page per city per service family,
    generated only for cities with an actual matched listing. Page layout is
    1) the filtered search map, 2) SEO content below it."""
    d = os.path.join(ROOT, "find")
    os.makedirs(d, exist_ok=True)

    families = []  # per family: {slug, name, short, url_prefix, entries: [(loc, matched, url_slug)], match_mode}
    for fam in FIND_PAGE_FAMILIES:
        slug = fam.get("service_slug")
        match_mode = fam.get("match_mode", "service")
        svc_name = fam.get("page_name") or (SERVICES[slug] if slug else "Bounce House Rentals")
        entries = []
        for loc in LOCATIONS:
            if match_mode in ("any", "theme"):
                matched = providers_for_location(loc, providers, limit=50)
            elif match_mode == "tag":
                matched = _providers_for_location_tag(loc, providers, fam["tag"])
            else:
                matched = _providers_for_location_service(loc, providers, slug)
            if not matched:
                continue
            url_slug = f'{fam["url_prefix"]}-{loc["slug"]}-ga'
            entries.append((loc, matched, url_slug))
        families.append({"slug": slug, "name": svc_name, "url_prefix": fam["url_prefix"],
                          "entries": entries, "match_mode": match_mode,
                          "map_filter": fam.get("map_filter", fam.get("tag")),
                          "desc_template": fam.get("desc_template"),
                          "theme_blurb": fam.get("theme_blurb"), "theme_note": fam.get("theme_note")})

    near_me = []  # {slug, name, matched, url_slug, url_prefix, svc_short}
    for slug in SERVICES:
        matched_all = [p for p in providers if slug in p["services"]]
        matched_all.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
        if not matched_all:
            continue
        override = NEAR_ME_OVERRIDES.get(slug)
        svc_name, url_prefix = override if override else (SERVICES[slug], slug)
        near_me.append({"slug": slug, "name": svc_name, "matched": matched_all,
                         "url_slug": f"{url_prefix}-near-me", "url_prefix": url_prefix,
                         "svc_short": SERVICES_SHORT.get(slug, "")})

    # Metro-wide "near me" pages for tag-based families too (Chair/Tent/Table/
    # Chiavari Chair Rentals) — matched the same way as their per-city pages,
    # just without the ZIP/location filter.
    for fam in FIND_PAGE_FAMILIES:
        if fam.get("match_mode") != "tag":
            continue
        tag = fam["tag"]
        matched_all = [p for p in providers if tag in extra_map_tags(p)]
        matched_all.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
        if not matched_all:
            continue
        near_me.append({"slug": fam.get("service_slug"), "name": fam.get("page_name") or tag,
                         "matched": matched_all, "url_slug": f'{fam["url_prefix"]}-near-me',
                         "url_prefix": fam["url_prefix"], "svc_short": fam.get("map_filter", tag)})

    # Metro-wide "near me" pages for "theme" families (e.g. Halloween Event
    # Rentals) — every provider counts as "closely tied," so this is never
    # empty as long as the directory has at least one listing.
    for fam in FIND_PAGE_FAMILIES:
        if fam.get("match_mode") != "theme":
            continue
        matched_all = sorted(providers, key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))
        if not matched_all:
            continue
        near_me.append({"slug": None, "name": fam.get("page_name") or fam["url_prefix"],
                         "matched": matched_all, "url_slug": f'{fam["url_prefix"]}-near-me',
                         "url_prefix": fam["url_prefix"], "svc_short": ""})

    # Flat list of every generated /find/ page, used to cross-link all of them
    # to each other so none are orphaned as more service families are added.
    all_find_pages = [
        {"title": f'{fam["name"]} in {loc["name"]}, GA', "url": f'/find/{url_slug}/'}
        for fam in families for loc, matched, url_slug in fam["entries"]
    ] + [
        {"title": f'{nm["name"]} Near Me', "url": f'/find/{nm["url_slug"]}/'}
        for nm in near_me
    ]

    # --- per-city landing pages ---
    for fam in families:
        slug = fam["slug"]
        match_mode = fam["match_mode"]
        svc_name = fam["name"]
        svc_short = fam.get("map_filter") or (SERVICES_SHORT.get(slug, "") if slug else "")
        for loc, matched, url_slug in fam["entries"]:
            nl = loc["name"]
            title = f"{svc_name} in {nl} Georgia"
            hoods3 = ", ".join(loc["neighborhoods"][:3])

            if match_mode == "any":
                # Full replacement for the old /locations/{slug}/ page: general
                # citywide content, not narrowed to one specific service.
                desc = f"Rent bounce houses, water slides and party rentals in {nl}, Georgia. Compare local providers, view pricing and get a free quote."
                page_intro = esc(loc["blurb"])
                map_heading = f"Bounce House Providers On the Map Near {esc(nl)}"
                map_desc = f"Browse party rental providers closest to {esc(nl)}. Click a listing or map pin to see details, ratings and reviews."
                map_service_param = ""
                map_zoom = 11

                prov_links = "\n          ".join(
                    f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>{prov_meta_html(p)}</li>'
                    for p in matched)
                svc_links_loc = "\n          ".join(
                    f'<li><a href="/services/{s}/">{SERVICES[s]} in {nl}</a></li>' for s in SERVICES)
                hoods = ", ".join(loc["neighborhoods"])
                landmarks = ", ".join(loc["landmarks"])
                zips = ", ".join(loc["zips"])
                nearby = [LOC_BY_SLUG[s] for s in loc.get("nearby", []) if s in LOC_BY_SLUG]
                nearby_links = "\n          ".join(
                    f'<li><a href="{location_href(x)}">Bounce House Rentals in {esc(x["name"])}</a></li>' for x in nearby)

                content_html = f'''
      <h2>Bounce House &amp; Party Rentals Serving {esc(nl)}</h2>
      <img class="content-photo" src="/images/hero-bounce-house.jpg" alt="Bounce house and slide combo set up for a birthday party near {esc(nl)}, Georgia" loading="lazy" width="1376" height="768">
      <p>Whether you are planning a birthday party, school field day, church festival or corporate family day in {esc(nl)}, our directory connects you with vetted local providers. Popular areas served include {esc(hoods)}, with delivery near {esc(landmarks)} and throughout ZIP codes {esc(zips)}.</p>

      <div class="callout">
        <p><strong>Serving all of {esc(nl)} and nearby Atlanta.</strong> Providers deliver bounce houses, water slides, obstacle courses, tents, tables, chairs and concessions with setup and teardown included.</p>
      </div>

      <h2>Rental Services Available in {esc(nl)}</h2>
      <ul class="bullet-services">
        {svc_links_loc}
      </ul>

      <h2>Bounce House Providers Near {esc(nl)}</h2>
      <p>These directory providers are based in or around {nl} and deliver across the area. Select a provider to view details, or <a href="#" data-wizard-open>request a free quote</a>:</p>
      <ul class="bullet-services">
        {prov_links}
      </ul>

      <h2>Looking for Cheap Bounce House Rentals in {esc(nl)}?</h2>
      <p>Compare budget-friendly options including $99 bounce house specials on our <a href="/cheap-bounce-house-rentals/">cheap bounce house rentals</a> page, or browse individual <a href="/bounce-houses/">bounce houses available to rent</a>.</p>

      <h2>Nearby Service Areas</h2>
      <ul>
        {nearby_links}
        <li><a href="/find/">View all Find pages</a></li>
      </ul>
'''
                faqs = [
                    (f"How much does it cost to rent a bounce house in {nl}?",
                     f"<p>In {nl}, a classic bounce house typically rents for about $120&ndash;$260 per day, with combo slides, water slides and obstacle courses running roughly $180&ndash;$900+ depending on size. Final pricing depends on your date, delivery distance and rental length. <a href=\"/cheap-bounce-house-rentals/\">See current $99 specials</a> or <a href=\"#\" data-wizard-open>request a free quote</a>.</p>"),
                    (f"Do providers deliver bounce houses to {nl}?",
                     f"<p>Yes. Directory providers deliver bounce houses, water slides, tents, tables, chairs and concessions throughout {nl}, including {esc(hoods3)}, and handle setup and pickup.</p>"),
                    (f"How far in advance should I book a bounce house in {nl}?",
                     f"<p>For weekend dates in {nl} during Atlanta's busy spring and summer season, book 2&ndash;4 weeks ahead. Last-minute requests are welcome too&mdash;<a href=\"#\" data-wizard-open>book now</a> and we'll check live availability.</p>"),
                    (f"What can I rent for a party in {nl}?",
                     f"<p>You can rent classic bounce houses, bounce-and-slide combos, water slides, obstacle courses, concession machines, tents, tables and chairs, interactive games and complete party packages. See <a href=\"/services/\">all services</a>.</p>"),
                ]
            elif match_mode == "theme":
                # Broad "closely tied services" match — every provider in the
                # city by ZIP, since bounce houses, tents/tables/chairs,
                # entertainment & staff, decor and party packages are all
                # relevant to a themed event like this. Guarantees a non-empty
                # provider list for every city the family generates a page for.
                desc = f"Find {svc_name.lower()} in {nl}, Georgia — bounce houses, tents, tables, chairs, entertainment, decor and other closely related rentals from {len(matched)} local providers. Free quotes."
                page_intro = f"Compare {len(matched)} {nl} provider{'s' if len(matched) != 1 else ''} offering rentals for {svc_name.lower().replace(' near me', '')}, with free quotes and no obligation."
                map_heading = f"{svc_name} Providers Near {esc(nl)}"
                map_desc = f"Browse {len(matched)} {nl} provider{'s' if len(matched) != 1 else ''} offering rentals closely tied to {svc_name.lower()}. Click a listing or map pin to see details, ratings and reviews."
                map_service_param = ""
                map_zoom = 11

                prov_links = "\n          ".join(
                    f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>{prov_meta_html(p)}</li>'
                    for p in matched)

                theme_blurb_tpl = fam.get("theme_blurb") or (
                    "Planning {svc_lower} in {city}? The local providers below offer bounce houses, tents, tables and "
                    "chairs, entertainment and staff, decor and other rentals closely tied to this kind of event, including {hoods}.")
                theme_note = fam.get("theme_note") or (
                    "Providers deliver bounce houses, tents, tables, chairs, entertainment and staff, and decor with "
                    "setup and teardown included.")
                theme_blurb = theme_blurb_tpl.format(city=esc(nl), hoods=esc(hoods3), svc_lower=svc_name.lower())

                content_html = f'''
      <h2>{svc_name} in {esc(nl)}, Georgia</h2>
      {featured_image_html(fam["url_prefix"], alt_override=f"{svc_name} rentals set up for an event near {nl}, Georgia")}
      <p>{theme_blurb}</p>

      <div class="callout">
        <p><strong>Serving all of {esc(nl)} and nearby Atlanta.</strong> {theme_note}</p>
      </div>

      <h2>{nl} Providers for {svc_name}</h2>
      <ul class="bullet-services">
          {prov_links}
      </ul>

      <p><a href="/find/">&larr; Back to the Find hub</a> &middot; <a href="/services/">See all Atlanta rental services</a> &middot; <a href="{location_href(loc)}">More rentals in {esc(nl)}</a></p>
'''
                faqs = [
                    (f"What can I rent for {svc_name.lower()} in {nl}?",
                     f"<p>Providers in {nl} offer bounce houses, tents, tables and chairs, entertainment and staff, decor and full party packages &mdash; all closely tied to this kind of event. <a href=\"#\" data-wizard-open>Request a free quote</a> to see what's available for your date.</p>"),
                    (f"Do providers deliver {svc_name.lower()} to {nl}?",
                     f"<p>Yes. The {len(matched)} directory provider{'s' if len(matched) != 1 else ''} listed below deliver, set up and tear down rentals throughout {nl}, including {esc(hoods3)}.</p>"),
                    (f"How do I book {svc_name.lower()} in {nl}?",
                     f"<p>Click <a href=\"#\" data-wizard-open>Book Now</a> to tell us about your event and we'll match you with an available {nl} provider for your date.</p>"),
                ]
            else:
                if fam.get("desc_template"):
                    n = len(matched)
                    is_are = "is" if n == 1 else "are"
                    provider_word = "provider" if n == 1 else "providers"
                    desc = fam["desc_template"].format(n=n, city=nl, is_are=is_are, provider_word=provider_word)
                else:
                    desc = f"Rent {svc_name.lower()} in {nl}, Georgia. Compare {len(matched)} local providers, view pricing and get a free quote."
                page_intro = f"Compare {len(matched)} {nl} provider{'s' if len(matched) != 1 else ''} offering {svc_name.lower()}, with free quotes and no obligation."
                map_heading = f"{svc_name} Providers Near {esc(nl)}"
                map_desc = f"Browse {len(matched)} {nl} provider{'s' if len(matched) != 1 else ''} offering {svc_name.lower()}. Click a listing or map pin to see details, ratings and reviews."
                map_service_param = svc_short
                map_zoom = 12

                prov_links = "\n          ".join(
                    f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>{prov_meta_html(p)}</li>'
                    for p in matched)

                content_html = f'''
      <h2>{svc_name} in {esc(nl)}, Georgia</h2>
      {featured_image_html(fam["url_prefix"], alt_override=f"{svc_name} set up for an event near {nl}, Georgia")}
      <p>Planning an event in {esc(nl)}? The providers below deliver, set up and tear down {svc_name.lower()} throughout {esc(nl)}, including {esc(hoods3)}. Whether you need seating for a backyard birthday or a full tent setup for a wedding reception, compare pricing and reviews before you book.</p>

      <h2>{nl} Providers Offering {svc_name}</h2>
      <ul class="bullet-services">
          {prov_links}
      </ul>

      <p><a href="/find/">&larr; Back to the Find hub</a> &middot; <a href="/services/{slug}/">See {svc_name} across all of Atlanta</a> &middot; <a href="{location_href(loc)}">More rentals in {esc(nl)}</a></p>
'''
                faqs = [
                    (f"How much do {svc_name.lower()} cost in {nl}?",
                     f"<p>In {nl}, {svc_name.lower()} typically run $90&ndash;$600+ depending on quantity, size and rental length. Final pricing depends on your date and delivery distance. <a href=\"#\" data-wizard-open>Request a free quote</a> for exact pricing.</p>"),
                    (f"Do providers deliver {svc_name.lower()} to {nl}?",
                     f"<p>Yes. The {len(matched)} directory provider{'s' if len(matched) != 1 else ''} listed below deliver, set up and tear down {svc_name.lower()} throughout {nl}, including {esc(hoods3)}.</p>"),
                    (f"How do I book {svc_name.lower()} in {nl}?",
                     f"<p>Click <a href=\"#\" data-wizard-open>Book Now</a> to tell us about your event. We'll match you with available {nl} providers for your date.</p>"),
                ]

            faq_html, faq_ld = faq_block(faqs)

            other_pages = [fp for fp in all_find_pages if fp["url"] != f"/find/{url_slug}/"]
            other_find_html = ""
            if other_pages:
                other_find_links = "\n          ".join(
                    f'<li><a href="{fp["url"]}">{esc(fp["title"])}</a></li>' for fp in other_pages)
                other_find_html = f'''
      <h2>More Find Pages</h2>
      <ul class="bullet-services">
          {other_find_links}
      </ul>'''

            svc_ld = {"@context": "https://schema.org", "@type": "Service", "serviceType": svc_name,
                      "areaServed": {"@type": "Place", "name": f"{nl}, Georgia"},
                      "provider": {"@type": "LocalBusiness", "name": "Atlanta Bounce House Rental Directory",
                                   "telephone": PHONE_HREF, "areaServed": f"{nl}, GA"},
                      "url": f"{DOMAIN}/find/{url_slug}/"}
            bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
                {"@type": "ListItem", "position": 2, "name": "Find", "item": DOMAIN + "/find/"},
                {"@type": "ListItem", "position": 3, "name": title, "item": f"{DOMAIN}/find/{url_slug}/"}]}
            extra = (f'<script type="application/ld+json">\n{json.dumps(svc_ld, ensure_ascii=False)}\n</script>\n'
                     f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}\n{LEAFLET_HEAD}')

            clat, clng = location_center(loc, providers)

            page = head(title, desc, f"{DOMAIN}/find/{url_slug}/", extra)
            page += header("find") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/find/">Find</a> &rsaquo; {esc(title)}</div>
    <h1>{title}</h1>
    <p>{page_intro}</p>
    {trust_strip(count=len(providers))}
  </div>
</div>

<section id="map" class="alt">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Explore the Map</div>
      <h2>{map_heading}</h2>
      <p>{map_desc}</p>
    </div>
    {searchmap_html(area=nl, lat=clat, lng=clng, zoom=map_zoom, service=map_service_param)}
  </div>
</section>

<section>
  <div class="container">
    <div class="content">
      {content_html}
      {other_find_html}
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Book {svc_name} in {esc(nl)} Today</h2>
    <p>Tell us about your event and we'll match you with available {esc(nl)} providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
            pd = os.path.join(d, url_slug)
            os.makedirs(pd, exist_ok=True)
            open(os.path.join(pd, "index.html"), "w").write(page)

    # --- "near me" metro-wide service pages ---
    for nm in near_me:
        slug = nm["slug"]
        svc_name = nm["name"]
        matched = nm["matched"]
        url_slug = nm["url_slug"]
        svc_short = nm["svc_short"]
        services_link = (f'<a href="/services/{slug}/">See {svc_name} details and pricing</a>' if slug
                          else f'<a href="/services/">See all Atlanta rental services</a>')
        title = f"{svc_name} Near Me"
        desc = f"Find {svc_name.lower()} near you across metro Atlanta, Georgia. Compare {len(matched)} local providers, view pricing and get a free quote."

        prov_links = "\n          ".join(
            f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>'
            f'{" &mdash; " + esc(p["city"]) + ", GA" if p.get("city") else ""}'
            f'{prov_meta_html(p)}</li>'
            for p in matched)

        same_service_cities = [fam for fam in families if fam["url_prefix"] == nm["url_prefix"] and fam["entries"]]
        city_links_html = ""
        if same_service_cities:
            city_links = "\n          ".join(
                f'<li><a href="/find/{url_slug2}/">{fam["name"]} in {esc(loc["name"])}, GA</a></li>'
                for fam in same_service_cities for loc, matched2, url_slug2 in fam["entries"])
            city_links_html = f'''
      <h2>{svc_name} by City</h2>
      <ul class="bullet-services">
          {city_links}
      </ul>'''

        top_rated = [p for p in matched if p.get("rating")][:3]
        top_rated_txt = ""
        if top_rated:
            names_bits = [f'{esc(p["name"])} ({p["rating"]}&#9733;, {p["reviews"] or 0} reviews)' for p in top_rated]
            if len(names_bits) == 1:
                top_rated_txt = names_bits[0]
            elif len(names_bits) == 2:
                top_rated_txt = f'{names_bits[0]} and {names_bits[1]}'
            else:
                top_rated_txt = f'{", ".join(names_bits[:-1])} and {names_bits[-1]}'

        avg_rating = None
        rated = [p["rating"] for p in matched if p.get("rating")]
        if rated:
            avg_rating = round(sum(rated) / len(rated), 1)

        faqs = [
            (f"Where can I find {svc_name.lower()} near me in Atlanta?",
             f"<p>Our directory lists {len(matched)} Atlanta-area provider{'s' if len(matched) != 1 else ''} offering {svc_name.lower()}. Use the map above to find the closest one to you, or <a href=\"#\" data-wizard-open>request a free quote</a> and we'll match you with an available provider.</p>"),
            (f"How much do {svc_name.lower()} cost?",
             f"<p>Pricing varies by provider, quantity and rental length. <a href=\"#\" data-wizard-open>Request a free quote</a> for exact pricing on your event.</p>"),
            (f"How do I book {svc_name.lower()} near me?",
             f"<p>Click <a href=\"#\" data-wizard-open>Book Now</a> to tell us about your event and we'll match you with an available provider near you.</p>"),
            (f"How far in advance should I reserve {svc_name.lower()}?",
             f"<p>For weekend dates during Atlanta's busy spring and summer event season, book 2&ndash;4 weeks ahead when possible &mdash; popular providers and dates fill up fastest. Need something last minute? <a href=\"#\" data-wizard-open>Request a free quote</a> and we'll check live availability with providers near you.</p>"),
            (f"Do {svc_name.lower()} providers deliver and set up?",
             f"<p>Yes. Directory providers offering {svc_name.lower()} in metro Atlanta typically include delivery, setup and teardown/pickup in their standard service area. Delivery radius and fees vary by provider and distance, so confirm details when you request your quote.</p>"),
            (f"What should I check before booking {svc_name.lower()} near me?",
             f"<p>Compare star rating, review count and Google verification status for each provider (shown on every listing below), confirm the provider services your ZIP code, and ask about delivery windows, setup time and any minimum order requirements for your event date.</p>"),
        ]
        faq_html, faq_ld = faq_block(faqs)

        seo_content_html = f'''
      <h2>Why Book {svc_name} Near You in Atlanta?</h2>
      <p>Booking {svc_name.lower()} from a provider near your event location in metro Atlanta keeps delivery costs down and makes setup and pickup faster and more reliable. Instead of searching one company at a time, this page puts every directory provider offering {svc_name.lower()} on one map so you can compare distance, pricing and reviews side by side before you request a quote.</p>

      <h2>How to Choose a {svc_name} Provider</h2>
      <p>Not every {svc_name.lower()} provider is the same. When comparing options near you, look at:</p>
      <ul class="bullet-services">
        <li><strong>Rating and review count</strong> &mdash; a high star rating backed by a large number of reviews is a stronger signal than a perfect score with only a handful of reviews.</li>
        <li><strong>Google verification</strong> &mdash; verified listings (marked on every card below) have confirmed business details on Google.</li>
        <li><strong>Distance and delivery radius</strong> &mdash; a closer provider usually means lower delivery fees and more flexible setup windows.</li>
        <li><strong>What else they offer</strong> &mdash; many providers bundle {svc_name.lower()} with related rentals, which can simplify booking and save on delivery if you need more than one item for your event.</li>
      </ul>
      {(f'<p>Some of the highest-rated options near you right now include {top_rated_txt}.</p>' if top_rated_txt else '')}

      <h2>{svc_name} Pricing in Atlanta</h2>
      <p>Exact pricing for {svc_name.lower()} depends on the provider, the quantity you need, your event date and delivery distance. {(f'Providers on this page currently average about {avg_rating}&#9733; across {sum(p.get("reviews") or 0 for p in matched)} combined Google reviews.' if avg_rating else '')} The most reliable way to get an accurate number is to request a free quote below &mdash; you will hear back directly from an available provider with pricing for your specific event.</p>

      <h2>Booking Tips for {svc_name}</h2>
      <p>Reserve as early as you can for weekend dates in Atlanta's peak spring and summer event season, since popular providers and inventory sell out first. Have your event date, ZIP code and estimated guest count ready when you request a quote &mdash; it helps providers give you a faster, more accurate response.</p>
'''

        other_pages = [fp for fp in all_find_pages if fp["url"] != f"/find/{url_slug}/"]
        other_find_html = ""
        if other_pages:
            other_find_links = "\n          ".join(
                f'<li><a href="{fp["url"]}">{esc(fp["title"])}</a></li>' for fp in other_pages)
            other_find_html = f'''
      <h2>More Find Pages</h2>
      <ul class="bullet-services">
          {other_find_links}
      </ul>'''

        svc_ld = {"@context": "https://schema.org", "@type": "Service", "serviceType": svc_name,
                  "areaServed": {"@type": "City", "name": "Atlanta"},
                  "provider": {"@type": "LocalBusiness", "name": "Atlanta Bounce House Rental Directory",
                               "telephone": PHONE_HREF},
                  "url": f"{DOMAIN}/find/{url_slug}/"}
        bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Find", "item": DOMAIN + "/find/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": f"{DOMAIN}/find/{url_slug}/"}]}
        extra = (f'<script type="application/ld+json">\n{json.dumps(svc_ld, ensure_ascii=False)}\n</script>\n'
                 f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}\n{LEAFLET_HEAD}')

        nm_photo = featured_image_html(
            nm["url_prefix"], alt_override=f"{svc_name} set up for an event in metro Atlanta, Georgia")

        page = head(title, desc, f"{DOMAIN}/find/{url_slug}/", extra)
        page += header("find") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/find/">Find</a> &rsaquo; {esc(title)}</div>
    <h1>{title}</h1>
    <p>Compare {len(matched)} Atlanta-area provider{"s" if len(matched) != 1 else ""} offering {svc_name.lower()}, with free quotes and no obligation.</p>
    {trust_strip(count=len(providers))}
  </div>
</div>

<section id="map" class="alt">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Explore the Map</div>
      <h2>{svc_name} Near You</h2>
      <p>Browse {len(matched)} provider{"s" if len(matched) != 1 else ""} offering {svc_name.lower()} across metro Atlanta. Click a listing or map pin to see details, ratings and reviews.</p>
    </div>
    {searchmap_html(area="Atlanta", zoom=10, service=svc_short)}
  </div>
</section>

<section>
  <div class="container">
    <div class="content">
      <h2>{svc_name} Near You in Metro Atlanta</h2>
      {nm_photo}
      <p>Whichever part of metro Atlanta you're in, the providers below offer {svc_name.lower()} with delivery, setup and teardown included. Compare ratings and reviews, then request a free quote.</p>
      {seo_content_html}
      <h2>Providers Offering {svc_name}</h2>
      <ul class="bullet-services">
          {prov_links}
      </ul>
      {city_links_html}

      <p><a href="/find/">&larr; Back to the Find hub</a> &middot; {services_link}</p>
      {other_find_html}
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Book {svc_name} Today</h2>
    <p>Tell us about your event and we'll match you with an available provider near you. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        pd = os.path.join(d, url_slug)
        os.makedirs(pd, exist_ok=True)
        open(os.path.join(pd, "index.html"), "w").write(page)

    # --- /find/ hub index ---
    near_me_links = "\n      ".join(
        f'<li><a href="/find/{nm["url_slug"]}/">{nm["name"]} Near Me</a> '
        f'<span class="muted">&mdash; {len(nm["matched"])} provider{"s" if len(nm["matched"]) != 1 else ""}</span></li>'
        for nm in near_me)
    near_me_html = ""
    if near_me:
        near_me_html = f'''    <h2>Rentals Near Me</h2>
    <ul class="bullet-services">
      {near_me_links}
    </ul>'''

    sections_html = []
    for fam in families:
        if not fam["entries"]:
            continue
        links = "\n      ".join(
            f'<li><a href="/find/{url_slug}/">{fam["name"]} in {esc(loc["name"])}, GA</a> '
            f'<span class="muted">&mdash; {len(matched)} provider{"s" if len(matched) != 1 else ""}</span></li>'
            for loc, matched, url_slug in fam["entries"])
        sections_html.append(f'''    <h2>{fam["name"]} by City</h2>
    <ul class="bullet-services">
      {links}
    </ul>''')
    sections = "\n\n".join(([near_me_html] if near_me_html else []) + sections_html)

    item_ld = {"@context": "https://schema.org", "@type": "ItemList",
               "itemListElement": [
                   {"@type": "ListItem", "position": i + 1,
                    "name": fp["title"],
                    "url": f'{DOMAIN}{fp["url"]}'}
                   for i, fp in enumerate(all_find_pages)]}
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
        {"@type": "ListItem", "position": 2, "name": "Find", "item": DOMAIN + "/find/"}]}
    extra = (f'<script type="application/ld+json">\n{json.dumps(item_ld, ensure_ascii=False)}\n</script>\n'
             f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n')

    hub = head(
        "Find Bounce House and Party Rentals in Atlanta, Georgia | Atlanta Bounce House Rentals",
        "Find exactly what you need — browse Atlanta Bounce House Rentals by service and city to compare local providers, view pricing and get a free quote.",
        DOMAIN + "/find/", extra)
    hub += header("find") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Find</div>
    <h1>Find Exactly What You Need</h1>
    <p>Every page below combines an interactive provider map with details on pricing, availability and reviews for a specific service in a specific Atlanta-area city &mdash; so you can compare and book faster.</p>
    <div class="find-search">
      <input id="find-search" type="search" placeholder="Search a service or city &mdash; e.g. photo booth, Buckhead, tent&hellip;" aria-label="Search find pages">
    </div>
    {trust_strip(count=len(providers))}
  </div>
</div>

<section>
  <div class="container content" style="max-width:none;" id="find-sections">
    {featured_image_html(alt_override="Atlanta party rentals set up for a celebration")}
    {sections}
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Can't Find Your City or Service?</h2>
    <p>Tell us about your event and we'll match you with available Atlanta providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
<script src="/js/find.js"></script>
</body>
</html>
'''
    open(os.path.join(d, "index.html"), "w").write(hub)

    find_urls = ["/find/"] + [fp["url"] for fp in all_find_pages]
    return find_urls


# ----------------------------------------------------------------- cheap / $99 landing
def build_cheap(providers):
    """High-intent landing page for 'cheap bounce house rentals near me' and
    '$99 bounce house rental' — both surfaced as ranking opportunities in GSC."""
    top = sorted(providers, key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0)))[:8]
    prov_links = "\n          ".join(
        f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>'
        f'{" &mdash; " + str(p["rating"]) + "&#9733;" if p.get("rating") else ""}</li>' for p in top)
    loc_links = "\n          ".join(
        f'<li><a href="{location_href(l)}">Cheap bounce house rentals in {esc(l["name"])}</a></li>'
        for l in LOCATIONS[:12])
    svc_links = "\n          ".join(
        f'<li><a href="/services/{s}/">{SERVICES[s]}</a></li>' for s in SERVICES)

    faqs = [
        ("Are there really $99 bounce house rentals in Atlanta?",
         f"<p>Yes. Several Atlanta providers offer entry-level bounce houses starting around $99 for a standard rental window, typically for smaller residential units booked on weekdays or off-peak weekends. Availability varies by date&mdash;call <a href=\"tel:{PHONE_HREF}\">{PHONE_DISPLAY}</a> to find a $99 special for your day.</p>"),
        ("How can I rent a cheap bounce house near me without sacrificing safety?",
         "<p>Every provider in our directory shows its Google rating and review count, and many are verified. Even budget rentals include commercial-grade, cleaned units with delivery and setup. Compare well-reviewed providers below to get a low price from a trusted company.</p>"),
        ("What is the cheapest day to rent a bounce house in Atlanta?",
         "<p>Weekdays and Sundays are usually the most affordable, as Saturday is the busiest party day. Booking early and choosing a smaller classic bounce house over a large combo or water slide also keeps costs down.</p>"),
        ("Do cheap bounce house rentals include delivery and setup?",
         f"<p>In most cases, yes&mdash;Atlanta providers include delivery, setup and teardown in the quoted price within their standard service radius. Confirm the delivery area for your ZIP code when you <a href=\"/#providers\">request a free quote</a> or call {PHONE_DISPLAY}.</p>"),
    ]
    faq_html, faq_ld = faq_block(faqs)
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
        {"@type": "ListItem", "position": 2, "name": "Cheap Bounce House Rentals", "item": DOMAIN + "/cheap-bounce-house-rentals/"}]}
    extra = f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}'

    page = head(
        "Cheap Bounce House Rentals in Atlanta, GA | $99 Specials & Budget Inflatables",
        "Find cheap bounce house rentals near you in Atlanta, including $99 specials. Compare budget-friendly, well-reviewed local providers and get a free quote. Call (401) 889-0182.",
        DOMAIN + "/cheap-bounce-house-rentals/", extra)
    page += header("") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Cheap Bounce House Rentals</div>
    <h1>Cheap Bounce House Rentals in Atlanta &mdash; Including $99 Specials</h1>
    <p>Renting a bounce house in Atlanta does not have to be expensive. Compare budget-friendly, well-reviewed local providers&mdash;some with bounce houses starting around $99&mdash;and request a free quote in minutes. Call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> to find today's lowest available price.</p>
  </div>
</div>

<section>
  <div class="container content" style="max-width:none;">
    <img class="content-photo" src="/images/hero-bounce-house.jpg" alt="Budget-friendly bounce house and slide combo set up for a birthday party in an Atlanta backyard" loading="lazy" width="1376" height="768">
    <h2>How to Get a Cheap Bounce House Rental Near You</h2>
    <p>The lowest prices in Atlanta usually come from booking a smaller classic bounce house, choosing a weekday or Sunday over a busy Saturday, and reserving early. Our directory makes it easy to compare providers side by side so you get a low price from a company you can trust&mdash;not just the cheapest listing.</p>

    <h2>$99 Bounce House Rental Specials</h2>
    <p>A $99 bounce house rental typically covers a standard residential unit during an off-peak window. Larger combo units, <a href="/services/water-slide-rentals/">water slides</a> and <a href="/services/obstacle-course-rentals/">obstacle courses</a> cost more, but full-day classic bouncers remain the most affordable way to keep kids entertained. Ask about $99 specials when you request your quote.</p>

    <h2>Affordable Providers in Our Atlanta Directory</h2>
    <p>These highly rated Atlanta providers are a great place to start for an affordable, reliable rental:</p>
    <ul class="bullet-services">
          {prov_links}
    </ul>

    <h2>Cheap Bounce House Rentals by Area</h2>
    <p>Find budget-friendly rentals in your part of the metro:</p>
    <ul class="bullet-services">
          {loc_links}
          <li><a href="/locations/">View all Atlanta service areas</a></li>
    </ul>

    <h2>Browse Affordable Rental Services</h2>
    <ul class="bullet-services">
          {svc_links}
    </ul>

    <div class="callout">
      <p><strong>Want to see specific units?</strong> Browse <a href="/bounce-houses/">bounce houses available to rent</a> with pricing, or <a href="/#providers">request a free quote</a> to compare the best deals for your date.</p>
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Get the Lowest Bounce House Price in Atlanta</h2>
    <p>Tell us about your event and we'll match you with the best-priced Atlanta providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Book Now &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "cheap-bounce-house-rentals")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(page)


# ----------------------------------------------------------------- leads
def build_leads():
    extra = ""
    html_out = head(
        "Live Atlanta Bounce House Rental Leads | Provider Board",
        "Live board of incoming bounce house and party rental leads across Atlanta, Georgia, from our quote form and phone line. Partners log in to view full contact details.",
        DOMAIN + "/leads.html", extra)
    html_out += header("leads") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Leads</div>
    <h1>Live Atlanta Rental Leads</h1>
    <p>Real-time inquiries from customers across Atlanta, captured through our website quote form and phone line. Directory partners log in to unlock full contact details and claim the job.</p>
  </div>
</div>

<section>
  <div class="container">
    {featured_image_html(alt_override="Atlanta party rentals set up for a celebration")}
    <div class="login-banner" id="login-banner">
      <div>
        <h3>You're viewing limited lead previews</h3>
        <p>Contact names, phone numbers and emails are hidden. Partners can log in to view full lead details and reach out directly.</p>
      </div>
      <button class="btn" data-open-login>Partner Log In</button>
    </div>

    <div class="leads-bar" id="logged-bar" style="display:none;">
      <span class="badge-live"><span class="dot"></span> Live feed &mdash; full access</span>
      <button class="btn btn-ghost" id="logout-btn">Log Out</button>
    </div>

    <div id="leads-board"></div>

    <div class="callout" style="margin-top:30px;">
      <p><strong>Want these leads?</strong> Join the Atlanta provider directory to get matched with customers in your service area. <a href="/legal/contact.html">Contact us to become a partner.</a></p>
    </div>
  </div>
</section>

<div class="modal-overlay" id="login-modal" role="dialog" aria-modal="true" aria-labelledby="login-title">
  <div class="modal">
    <button class="modal-close" data-close-login aria-label="Close">&times;</button>
    <h3 id="login-title">Partner Log In</h3>
    <p class="sub">Log in to view full lead contact details and claim jobs.</p>
    <div id="login-error" class="form-success" style="display:none;background:#fdeaea;border-color:#f3c2c2;color:#a12626;">
      Incorrect email or password. Please try again.
    </div>
    <form id="login-form" novalidate>
      <div class="field"><label for="l-email">Email</label><input id="l-email" name="email" type="email" placeholder="partner@atlbouncehouserentals.com" required></div>
      <div class="field"><label for="l-pass">Password</label><input id="l-pass" name="password" type="password" placeholder="********" required></div>
      <button class="btn btn-block" type="submit">Log In</button>
      <p class="form-note">Demo access &mdash; email: partner@atlbouncehouserentals.com &middot; password: atlanta2026</p>
    </form>
  </div>
</div>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/leads.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    open(os.path.join(ROOT, "leads.html"), "w").write(html_out)


# ----------------------------------------------------------------- legal
def build_legal():
    data = json.load(open(os.path.join(ROOT, "data", "legal-content.json")))
    for slug, p in data.items():
        page = head(p["title"], p["desc"], f"{DOMAIN}/legal/{slug}.html")
        page += header() + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; {p["h1"]}</div>
    <h1>{p["h1"]}</h1>
  </div>
</div>

<section>
  <div class="container content">
    {featured_image_html(alt_override="Atlanta party rentals set up for a celebration")}
    {p["body"]}
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        open(os.path.join(ROOT, "legal", slug + ".html"), "w").write(page)


def build_404():
    page = head("Page Not Found | Atlanta Bounce House Rentals", "Page not found.", DOMAIN + "/404.html")
    page = page.replace('<meta name="robots" content="index, follow">', '<meta name="robots" content="noindex">')
    page += header() + f'''
<section style="text-align:center;padding:90px 0;">
  <div class="container">
    <h1>404 &mdash; Page Not Found</h1>
    <p class="muted">The page you're looking for doesn't exist or has moved.</p>
    {featured_image_html(alt_override="Atlanta party rentals set up for a celebration")}
    <p style="margin-top:24px;"><a class="btn" href="/">Back to Home</a> &nbsp; <a class="btn btn-ghost" href="/services/">Browse Services</a></p>
  </div>
</section>

<script src="/js/main.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    open(os.path.join(ROOT, "404.html"), "w").write(page)


def build_llms(providers):
    """Generate /llms.txt (llmstxt.org) so answer engines and LLMs can quickly
    understand and cite the site."""
    svc_lines = "\n".join(
        f"- [{SERVICES[s]} in Atlanta]({DOMAIN}/services/{s}/): Pricing and providers for {SERVICES[s].lower()} across metro Atlanta."
        for s in SERVICES)
    top = sorted(providers, key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0)))[:15]
    prov_lines = "\n".join(
        f"- [{p['name']}]({DOMAIN}/partners/{p['slug']}/): {p['category']} in Atlanta, GA"
        + (f" — {p['rating']}★ ({p['reviews']} reviews)" if p["rating"] else "")
        for p in top)
    txt = f"""# Atlanta Bounce House Rentals

> Atlanta Bounce House Rentals (atlbouncehouserentals.com) is an independent directory that connects customers in Atlanta, Georgia with {len(providers)} local bounce house and party rental providers. Visitors compare providers by rating, reviews and verification, see typical price ranges, and request free quotes. Booking and quotes: call (401) 889-0182.

Key facts:
- Location served: Atlanta, Georgia and surrounding metro (Midtown, Buckhead, Decatur, Sandy Springs, College Park, East Point, Dunwoody, Chamblee and more).
- Phone for quotes and booking: (401) 889-0182
- Number of listed providers: {len(providers)}
- Typical price ranges: classic bounce houses ~$120-$260/day; combos, water slides and obstacle courses ~$180-$900+/day; full party packages ~$220-$1,800+.
- The site is a directory; it does not own equipment. Quotes are free and no-obligation.

## Services
{svc_lines}

## Top-rated providers
{prov_lines}

## Key pages
- [All services]({DOMAIN}/services/): Full list of bounce house and party rental categories in Atlanta.
- [Provider directory]({DOMAIN}/partners.html): All {len(providers)} providers with ratings, reviews and verification.
- [About]({DOMAIN}/legal/about.html): What the directory is and how it works.
- [Contact]({DOMAIN}/legal/contact.html): Phone, email and message form.
"""
    open(os.path.join(ROOT, "llms.txt"), "w").write(txt)


def build_sitemap(providers, find_urls=None):
    bh_items = json.load(open(os.path.join(ROOT, "data", "bounce-houses.json")))
    urls = ["/", "/services/", "/bounce-houses/", "/locations/",
            "/cheap-bounce-house-rentals/", "/partners.html", "/leads.html"]
    urls += [f"/services/{s}/" for s in SERVICES]
    urls += [f"/services/{slug}/" for slug, _ in SPECIALTY_SLUGS]
    urls += [f"/bounce-houses/{it['slug']}/" for it in bh_items]
    urls += [f"/locations/{l['slug']}/" for l in LOCATIONS if l["slug"] not in MIGRATED_LOCATION_SLUGS]
    urls += find_urls or []
    urls += [f"/legal/{s}.html" for s in ["about", "contact", "privacy-policy", "terms", "disclaimer"]]
    urls += [f"/partners/{it['slug']}/" for it in providers]
    items = "\n".join(
        f"  <url><loc>{DOMAIN}{u}</loc></url>" for u in urls)
    sm = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>
'''
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(sm)


def main():
    providers = json.load(open(os.path.join(ROOT, "data", "providers.json")))
    for it in providers:
        it["services"] = map_services(it)
    providers.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))

    MIGRATED_LOCATION_SLUGS.clear()
    MIGRATED_LOCATION_SLUGS.update(
        loc["slug"] for loc in LOCATIONS if providers_for_location(loc, providers))

    build_map_data(providers)
    build_index(providers)
    build_partners(providers)
    build_partner_pages(providers)
    build_services_index()
    build_service_pages(providers)
    build_specialty_service_pages()
    build_bounce_houses()
    build_locations(providers)
    find_urls = build_find_pages(providers)
    build_cheap(providers)
    build_leads()
    build_legal()
    build_404()
    build_sitemap(providers, find_urls)
    build_llms(providers)
    print(f"Built site: {len(providers)} providers + services + bounce houses + legal + leads + llms.txt")


if __name__ == "__main__":
    main()
