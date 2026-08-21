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
from urllib.parse import quote as urlquote

ROOT = os.path.dirname(os.path.abspath(__file__))
PHONE_DISPLAY = "404-737-1843"
PHONE_HREF = "+14047371843"
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


def directions_url(it):
    addr = it.get("address") or f'{it.get("city", "")}, {it.get("state", "")}'
    return "https://www.google.com/maps/dir/?api=1&destination=" + urlquote(addr)


def reviews_url(it):
    q = f'{it.get("name", "")} {it.get("city", "")} {it.get("state", "")} reviews'
    return "https://www.google.com/search?q=" + urlquote(q)


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
        <div class="header-search" id="header-search">
          <input type="search" id="site-search-input" placeholder="Search the site&hellip;" aria-label="Search the site" autocomplete="off">
          <div class="header-search-results" id="site-search-results" hidden></div>
        </div>
        <a href="/"{cls("home")}>Home</a>
        <a href="/cities/"{cls("cities")}>By City</a>
        <a href="/services/"{cls("services")}>By Service</a>
      </nav>
      <div class="header-ctas">
        <a class="header-call-cta" href="tel:{PHONE_HREF}">
          <span class="header-call-number">{PHONE_DISPLAY}</span>
          <span class="header-call-label">Call or text for quote</span>
        </a>
        <a class="book-now-cta" href="#" data-wizard-open>Free Instant Quote</a>
      </div>
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
        <a href="/leads/">Leads</a>
        <a href="/dashboard/">Site Analytics</a>
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
          <td class="book"><button type="button" class="table-book-btn" data-wizard-open aria-label="Book {esc(it["name"])}">Free Instant Quote</button></td>
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


def build_index(providers, families):
    groups = service_family_groups(families)
    counts = {s: sum(1 for p in providers if s in p["services"]) for s in SERVICES}

    def home_service_block(slug):
        # Only the primary family's cities are shown here (the homepage stays
        # scannable); the full breakdown with every tag/variant family lives
        # on /services/.
        fams = [f for f in groups.get(slug, []) if f["match_mode"] != "tag"]
        cities_html = ""
        if fams:
            fam = fams[0]
            cities_html = "\n      ".join(
                f'<li><h3><a href="{city_service_href(fam["url_prefix"], loc["slug"])}">{esc(SERVICES[slug])} in {esc(loc["name"])}</a></h3></li>'
                for loc, matched, _ in fam["entries"])
            cities_html = f'<ul class="home-service-cities">\n      {cities_html}\n    </ul>'
        count_html = (f'<p class="home-service-count">{counts[slug]} provider{"s" if counts[slug] != 1 else ""}</p>'
                      if counts[slug] else "")
        return f'''<div class="home-service-block">
      <h2><a href="/services/{slug}/">{esc(SERVICES[slug])} in Atlanta Georgia</a></h2>
      {count_html}
      {cities_html}
    </div>'''

    svc_blocks = "\n    ".join(home_service_block(s) for s in SERVICES)
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
         "<p>Click <a href=\"#\" data-wizard-open>Free Instant Quote</a> in the header or at the top of this page. Tell us your event type, date, ZIP code and what you need, and we'll match you with available Atlanta directory providers so you can compare and book.</p>"),
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
{faq_ld}'''
    html_out = head(
        "Atlanta Bounce House Rental Directory | Connect With All Providers And Compare",
        "Atlanta Bounce House Rental directory connecting you with all local providers. Search by service, compare bounce houses, water slides, obstacle courses and party rentals across Atlanta, Georgia. Free quotes.",
        DOMAIN + "/", extra)
    html_out += header("home") + f'''
<section class="hero">
  <div class="container">
    <div class="hero-copy">
      <h1>Atlanta's Most Complete Party Rental Directory</h1>
      <p class="lead">The best resource for finding bounce house, water slide, chiavari chair and every other party rental service in the Atlanta area &mdash; compare {len(providers)} trusted local providers and get a free quote in minutes.</p>
      <ul class="hero-points">
        <li>{len(providers)} verified Atlanta-area providers, all in one place</li>
        <li>Compare pricing, ratings and reviews before you call</li>
        <li>One request connects you with multiple free quotes</li>
      </ul>
      <div class="hero-ctas">
        <a class="header-call-cta hero-call-cta" href="tel:{PHONE_HREF}">
          <span class="header-call-number">{PHONE_DISPLAY}</span>
          <span class="header-call-label">Call or text for a free quote</span>
        </a>
        <a class="btn hero-quote-btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
      </div>
    </div>
  </div>
</section>

<section class="alt" id="how-we-help">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Why Atlanta Chooses Us</div>
      <h2>How We Help Atlanta Families Find the Right Rental</h2>
      <p>Every week we connect Atlanta hosts and planners with the right local provider for their event &mdash; here's a look at how it plays out across our most-requested categories.</p>
    </div>
    <div class="grid grid-3">
      <div class="card">
        <h3>Bounce Houses</h3>
        <p>A Buckhead parent needed a bounce house for a Saturday birthday party with only a few days' notice. One Free Instant Quote request connected her with several available Atlanta providers the same afternoon, and she had a classic bounce house booked within the hour.</p>
      </div>
      <div class="card">
        <h3>Chiavari Chairs</h3>
        <p>An East Atlanta wedding planner was comparing chiavari chair rentals for a 150-guest reception. Instead of calling around individually, our directory let her compare pricing and reviews from multiple providers side by side and pick the best fit.</p>
      </div>
      <div class="card">
        <h3>Water Slides</h3>
        <p>A Sandy Springs summer camp needed a water slide rental durable enough for back-to-back groups all day. We matched them with a highly-rated provider experienced in commercial-scale bookings, delivered and set up before camp started.</p>
      </div>
    </div>
  </div>
</section>

<section id="services">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">What You Can Rent</div>
      <h2>All Bounce House Rental Services In Atlanta Georgia</h2>
      <p>Explore every rental category available across the Atlanta metro and request a free quote on any of them. See the <a href="/services/">full breakdown by city</a> for even more options.</p>
    </div>
    <img class="content-photo" src="/images/hero-bounce-house.jpg" alt="Colorful bounce house and slide combo set up in a backyard for a birthday party in Atlanta, Georgia" loading="lazy" width="1376" height="768">
    <div class="home-services-list">
    {svc_blocks}
    </div>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
    <p>Browse {len(providers)} bounce house and party rental businesses serving Atlanta and the surrounding Georgia metro. Compare ratings and reviews, then click Free Instant Quote to tell us about your event and get matched with the right provider.</p>
  </div>
</div>

<section>
  <div class="container">
    {featured_image_html(alt_override="Atlanta party rental providers set up for a celebration")}
{provider_table(providers)}
    <div class="callout" style="margin-top:26px;">
      <p><strong>Ready to book?</strong> Use the <a href="#" data-wizard-open>Free Instant Quote</a> wizard to tell us about your event and we'll connect you with an available Atlanta company in minutes. Free quotes, no obligation.</p>
    </div>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">
          <a class="btn btn-ghost" href="{directions_url(it)}" target="_blank" rel="noopener"
            data-analytics-event="directions_click" data-analytics-listing="{esc(slug)}"
            data-analytics-name="{esc(name)}" data-analytics-city="{esc(it["city"])}">Get Directions</a>
          <a class="btn btn-ghost" href="{reviews_url(it)}" target="_blank" rel="noopener"
            data-analytics-event="review_click" data-analytics-listing="{esc(slug)}"
            data-analytics-name="{esc(name)}" data-analytics-city="{esc(it["city"])}">Read Reviews</a>
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
          <a class="btn btn-block" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
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

<script src="/js/map-data.js"></script>
<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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


# ----------------------------------------------------------------- listicle format
# Shared "numbered directory list" card/controls used by /cities/ and /services/
# listicle pages (search + filter + sort + list/map toggle, no spotlight card).
AVATAR_COLORS = ["#3a93d6", "#e0793c", "#2f9e6b", "#a25fd1", "#d64550", "#1f8fa3", "#c78a1e"]


def listicle_blurb(p, rank):
    name, city = esc(p["name"]), esc(p["city"])
    if p["rating"] and p["reviews"]:
        rating_txt = f'rated {p["rating"]} out of 5 from {p["reviews"]} reviews'
    elif p["reviews"]:
        rating_txt = f'with {p["reviews"]} Google reviews'
    else:
        rating_txt = "newly listed"
    if rank == 1:
        return f"{name} in {city} takes the top spot, {rating_txt}."
    if rank == 2:
        return f"{name}, out in {city}, is next up, {rating_txt}."
    return f"{name} in {city} is {rating_txt}."


def listicle_card_html(p, rank):
    initial = esc((p["name"][:1] or "?").upper())
    color = AVATAR_COLORS[sum(ord(c) for c in p["slug"]) % len(AVATAR_COLORS)]
    if p["rating"]:
        rating_html = (f'<span class="stars">{stars(p["rating"])}</span> {p["rating"]} '
                        f'<span class="muted">({p["reviews"] or 0} reviews)</span>')
    elif p["reviews"]:
        rating_html = f'<span class="muted">{p["reviews"]} reviews</span>'
    else:
        rating_html = '<span class="muted">New listing</span>'
    addr = esc(p["address"]) or esc(f'{p["city"]}, {p["state"]}')
    hours_json = esc(json.dumps(hours_map(p)))
    svc_attr = esc(",".join(p.get("services", [])))
    return f'''    <article class="lc-card" data-lc-name="{esc(p["name"].lower())}" data-lc-city="{esc(p["city"].lower())}"
      data-lc-services="{svc_attr}" data-lc-rating="{p["rating"] or 0}" data-lc-reviews="{p["reviews"] or 0}"
      data-lc-lat="{p["lat"] or ""}" data-lc-lng="{p["lng"] or ""}" data-hours='{hours_json}'>
      <span class="lc-rank">{rank}</span>
      <div class="lc-avatar" style="background:{color};" aria-hidden="true">{initial}</div>
      <div class="lc-body">
        <h3><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a></h3>
        <div class="lc-meta">{rating_html} &middot; {esc(p["city"])}, {esc(p["state"])} <span class="lc-distance-badge" hidden></span></div>
        <div class="lc-addr">{addr}</div>
        <div class="lc-hours" data-hours-text>Call to confirm today's hours</div>
        <p class="lc-blurb">{listicle_blurb(p, rank)}</p>
      </div>
      <div class="lc-actions">
        <a class="btn" href="/partners/{p["slug"]}/">View Details</a>
        <a class="btn btn-ghost" href="#" data-wizard-open>Free Instant Quote</a>
        <a class="lc-link" href="{directions_url(p)}" target="_blank" rel="noopener"
          data-analytics-event="directions_click" data-analytics-listing="{esc(p["slug"])}"
          data-analytics-name="{esc(p["name"])}" data-analytics-city="{esc(p["city"])}">Directions</a>
        <a class="lc-link" href="{reviews_url(p)}" target="_blank" rel="noopener"
          data-analytics-event="review_click" data-analytics-listing="{esc(p["slug"])}"
          data-analytics-name="{esc(p["name"])}" data-analytics-city="{esc(p["city"])}">Reviews</a>
      </div>
    </article>'''


def listicle_controls_html(items, kind_singular, kind_plural, area_word,
                            filter_label, filter_options_html, container_id):
    count = len(items)
    return f'''
<div class="lc-toolbar">
  <div class="lc-count">{count} {kind_plural if count != 1 else kind_singular} on this page</div>
  <div class="lc-view-toggle" role="group" aria-label="View toggle">
    <button type="button" class="lc-view-btn active" data-lc-view="list">List</button>
    <button type="button" class="lc-view-btn" data-lc-view="map">Map</button>
  </div>
</div>
<div class="lc-controls" id="{container_id}-controls">
  <input type="search" class="lc-search" placeholder="Search by name or {area_word}&hellip;" aria-label="Search listings">
  <div class="lc-controls-row">
    <label class="lc-select-wrap">{filter_label}
      <select class="lc-filter">
        <option value="">All</option>
        {filter_options_html}
      </select>
    </label>
    <label class="lc-select-wrap">Sort
      <select class="lc-sort">
        <option value="rating">Top rated</option>
        <option value="reviews">Most reviews</option>
        <option value="name">Name A-Z</option>
        <option value="distance">Distance</option>
      </select>
    </label>
    <button type="button" class="btn btn-ghost lc-reset">Reset</button>
    <button type="button" class="btn btn-ghost lc-distance">Show distance from me</button>
  </div>
  <div class="lc-count-live muted">{count} {kind_plural if count != 1 else kind_singular}</div>
</div>'''


def listicle_section_html(items, kind_singular, kind_plural, area_word,
                           filter_label, filter_options_html, map_html, container_id):
    """Full listicle: toolbar + controls + numbered card list + hidden map view.
    No spotlight/featured card — every listing appears once, in rank order."""
    cards_html = "\n".join(listicle_card_html(p, i + 1) for i, p in enumerate(items))
    empty_html = (f'<div class="info-box" style="text-align:center;"><h3>No {kind_plural} yet</h3>'
                  f'<p class="muted" style="margin:0;">Check back soon or <a href="#" data-wizard-open>request a free quote</a> '
                  f'and we will match you with an available provider.</p></div>') if not items else ""
    return f'''{listicle_controls_html(items, kind_singular, kind_plural, area_word, filter_label, filter_options_html, container_id)}
<div class="lc-list" id="{container_id}-list" data-lc-list>
{cards_html}
</div>
<p class="lc-no-results muted" data-lc-empty hidden>No listings match your search or filter.</p>
{empty_html}
<div class="lc-map-view" id="{container_id}-map" data-lc-map hidden>
  {map_html}
</div>'''


# Cities with at least one matched provider get a full programmatic /find/
# page instead of a /locations/ page (populated in main() before any builder
# that links to a location runs). Cities with zero matched providers keep
# their /locations/ page as a general, provider-list-free landing page.
MIGRATED_LOCATION_SLUGS = set()

# {city_slug: [(url_prefix, page_name, provider_count), ...]} — every
# /cities/{city}/{service}/ page that exists. Populated in main() before any
# builder that links to one runs.
CITY_SERVICE_INDEX = {}


def location_href(loc):
    """Where a link to this location should point — the /cities/ listicle page
    if the city has been migrated, otherwise the original /locations/ page."""
    slug = loc["slug"]
    if slug in MIGRATED_LOCATION_SLUGS:
        return f"/cities/{slug}/"
    return f"/locations/{slug}/"


# The "bounce-house-rentals" family matches EVERY provider in a city
# regardless of service, which is exactly what /cities/{city}/ already lists.
# Rather than ship two near-identical pages, that family's per-city URLs fold
# into the city page itself (301 from the old /find/ URL); every other family
# gets its own /cities/{city}/{service}/ page.
CITY_HUB_FAMILY_PREFIX = "bounce-house-rentals"


def city_service_href(url_prefix, loc_slug):
    """Canonical path for a city+service page. The old flat
    /find/{service}-{city}-ga/ URLs 301 here (see build_vercel_config)."""
    if url_prefix == CITY_HUB_FAMILY_PREFIX:
        return f"/cities/{loc_slug}/"
    return f"/cities/{loc_slug}/{url_prefix}/"


def legacy_find_path(url_prefix, loc_slug):
    """The pre-migration /find/ URL for a city+service page, kept only so the
    redirect map can be generated from the same data that builds the pages."""
    return f"/find/{url_prefix}-{loc_slug}-ga/"


def compute_find_families(providers):
    """Per-family list of the cities that have at least one matched provider.
    Shared by build_cities(), build_services_index() and build_find_pages() so
    all three agree on exactly which city+service pages exist."""
    families = []
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
            entries.append((loc, matched, f'{fam["url_prefix"]}-{loc["slug"]}-ga'))
        families.append({"slug": slug, "name": svc_name, "url_prefix": fam["url_prefix"],
                          "entries": entries, "match_mode": match_mode,
                          "map_filter": fam.get("map_filter", fam.get("tag")),
                          "desc_template": fam.get("desc_template"),
                          "theme_blurb": fam.get("theme_blurb"), "theme_note": fam.get("theme_note")})
    return families


def city_service_index(families):
    """{city_slug: [(url_prefix, page_name, provider_count), ...]} for every
    city+service page that gets its own URL (i.e. excluding the city-hub
    family), so city pages and the services hub can link to them."""
    by_city = {}
    for fam in families:
        if fam["url_prefix"] == CITY_HUB_FAMILY_PREFIX:
            continue
        for loc, matched, _ in fam["entries"]:
            by_city.setdefault(loc["slug"], []).append((fam["url_prefix"], fam["name"], len(matched)))
    for slug in by_city:
        by_city[slug].sort(key=lambda t: t[1].lower())
    return by_city



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
             f"<p>Click <a href=\"#\" data-wizard-open>Free Instant Quote</a> to tell us about your event. We'll match you with available Atlanta providers that offer {nml} for your date.</p>"),
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
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
        "Browse bounce houses available for rent across Atlanta, Georgia. Classic castles, rainbow combos and more — setup and teardown included. Call 404-737-1843 for pricing and availability.",
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
            f'Rent the {it["name"]} in Atlanta, Georgia. {it["tagline"]} Starting at ${it["pricing"][0]["price"]}. Call 404-737-1843 or request a quote.',
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
          <a class="btn btn-block" href="#" data-wizard-open style="margin-bottom:14px;">Free Instant Quote &rsaquo;</a>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
    ("bar-beverage-equipment-rentals", "Bar & Beverage Equipment Rentals Atlanta"),
    ("chair-rentals", "Chair Rentals Atlanta"),
    ("table-rentals", "Table Rentals Atlanta"),
]


# ----------------------------------------------------------------- products
# Individual rentable items with a real per-unit rate that we fulfil
# ourselves (rather than matching out to a directory provider). Each one gets
# a product-request page at /services/{parent_slug}/{slug}/ with a quantity
# picker, live running total and an order form that writes straight to the
# Supabase leads table with everything needed to raise an invoice and
# drop-service the order — see supabase/migrate_product_orders.sql.
#
# Standard delivery: flat fee, drop-off/pickup only (no setup), same policy
# for every product on this list.
PRODUCT_DELIVERY_FEE = 200.00
PRODUCT_DELIVERY_POLICY = {
    "hours": [
        ("Off-season", "Monday&ndash;Friday, 8am&ndash;5pm"),
        ("Peak season", "Monday&ndash;Saturday, 8am&ndash;5pm"),
    ],
    "included": [
        "Drop-off and pickup only &mdash; this is not a setup service.",
        "Delivery and pickup are made within 50ft of the truck, on a flat, hard, ground-level surface with no steps or obstructions.",
        "You're responsible for rinsing, repacking and stacking equipment the same way it was delivered.",
    ],
}
PRODUCTS = [
    {
        "slug": "gold-chiavari-chair-white-pad",
        "parent_slug": "chiavari-chair-rentals",
        "parent_name": "Chiavari Chair Rentals Atlanta",
        "name": "Gold Chiavari Chair with White Pad",
        "short_name": "Gold Chiavari Chair",
        "category": "Chairs & Benches",
        "price": 10.50,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Includes Velcro Hard-Back Cushion",
        "image": "/images/products/gold-chiavari-chair-white-pad.jpg",
        "image_alt": "Gold Chiavari chair with a white Velcro hard-back cushion, available to rent in Atlanta, Georgia",
        "image_w": 500, "image_h": 500,
        "options": [],
        "specs": [
            ("Seat Height", '17.75"H'),
            ("Overall Width", '15.75"W'),
            ("Overall Depth", '18"D'),
            ("Overall Height", '36.25"H'),
            ("Weight Capacity", "500 lbs."),
        ],
        "description": (
            "Introducing our Gold Chiavari Chair: the epitome of elegance for your event's seating. "
            "With its luxurious gold color and classic Chiavari design, this chair adds a touch of "
            "opulence to any setting. Ideal for weddings, galas, or upscale gatherings, its timeless "
            "appeal elevates the ambiance of any event. Impress your guests with our Gold Chiavari "
            "Chair, where style meets sophistication in every seat."
        ),
    },
    {
        "slug": "ghost-chair-clear",
        "parent_slug": "ghost-chair-rentals",
        "parent_name": "Ghost Chair Rentals Atlanta",
        "name": "Ghost Chair - Clear",
        "short_name": "Clear Ghost Chair",
        "category": "Chairs & Benches",
        "price": 17.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Clear round-back acrylic chair",
        "image": "/images/products/ghost-chair-clear.jpg",
        "image_alt": "Clear round-back acrylic Ghost chair, available to rent in Atlanta, Georgia",
        "image_w": 620, "image_h": 620,
        "options": [],
        "specs": [
            ("Seat Height", '17.75"H'),
            ("Overall Width", '15.75"W'),
            ("Overall Depth", '18"D'),
            ("Overall Height", '36.25"H'),
            ("Weight Capacity", "1,100 lbs."),
        ],
        "description": (
            "Introducing our Clear Round Back Ghost Chair: the epitome of modern elegance for your "
            "event's seating. With its transparent design and sleek round back, this chair adds a "
            "contemporary touch to any setting. Perfect for weddings, upscale parties, or modern "
            "gatherings, its unique appearance complements various decor styles. Elevate your event's "
            "ambiance and impress your guests with our Clear Round Back Ghost Chair, where style meets "
            "transparency in every seat."
        ),
    },
    {
        "slug": "chiavari-barstool-chair-fruitwood",
        "parent_slug": "chiavari-chair-rentals",
        "parent_name": "Chiavari Chair Rentals Atlanta",
        "name": "Chiavari Barstool Chair - Fruitwood",
        "short_name": "Fruitwood Chiavari Barstool",
        "category": "Chairs & Benches",
        "price": 30.00,
        "unit": "barstool",
        "unit_plural": "barstools",
        "min_qty": 1,
        "delivery_only": True,
        "includes": 'Use for 42" high-top tables and bars',
        "image": "/images/products/chiavari-barstool-chair-fruitwood.jpg",
        "image_alt": "Fruitwood Chiavari barstools lined up at a 42-inch high-top table for a cocktail-style event in Atlanta, Georgia",
        "image_w": 640, "image_h": 963,
        "options": [],
        "specs": [
            ("Use For", '42" high-top tables and bars'),
            ("Overall Width", '15-3/4"'),
            ("Overall Depth", '17"'),
            ("Overall Height", '45"'),
            ("Seat Width", '15-3/4"'),
            ("Seat Depth", '15-1/2"'),
            ("Seat Height", '28-3/4"'),
        ],
        "description": (
            "Introducing our Fruitwood Chiavari Barstool: a touch of rustic charm for your event's "
            "seating. With its warm fruitwood color and classic Chiavari design, this barstool adds "
            "elegance to any bar or high-top table. Ideal for weddings, cocktail parties, or upscale "
            "events, its timeless appeal complements any decor. Elevate your event's ambiance and "
            "provide stylish seating with our Fruitwood Chiavari Barstool, where comfort meets "
            "sophistication at every perch."
        ),
    },
    {
        "slug": "chiavari-chair-with-pad-white",
        "parent_slug": "chiavari-chair-rentals",
        "parent_name": "Chiavari Chair Rentals Atlanta",
        "name": "Chiavari Chair with Pad - White",
        "short_name": "White Chiavari Chair",
        "category": "Chairs & Benches",
        "price": 10.50,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Includes Velcro Hard-Back Cushion",
        "image": "/images/products/chiavari-chair-with-pad-white.jpg",
        "image_alt": "White Chiavari chairs with cushions set at a table with a burlap and lace runner for an outdoor wedding reception in Atlanta, Georgia",
        "image_w": 640, "image_h": 480,
        "options": [],
        "specs": [
            ("Seat Height", '17.75"H'),
            ("Overall Width", '15.75"W'),
            ("Overall Depth", '18"D'),
            ("Overall Height", '36.25"H'),
            ("Weight Capacity", "500 lbs."),
        ],
        "description": (
            "Introducing our White Chiavari Chair: the perfect fusion of elegance and versatility for "
            "your event's seating. With its crisp white color and classic Chiavari design, this chair "
            "adds a touch of sophistication to any setting. Ideal for weddings, banquets, or upscale "
            "gatherings, its timeless appeal complements a variety of decor styles. Elevate your event's "
            "ambiance and impress your guests with our White Chiavari Chair, where comfort meets style "
            "in every seat."
        ),
    },
    {
        "slug": "chiavari-chair-with-pad-silver",
        "parent_slug": "chiavari-chair-rentals",
        "parent_name": "Chiavari Chair Rentals Atlanta",
        "name": "Chiavari Chair with Pad - Silver",
        "short_name": "Silver Chiavari Chair",
        "category": "Chairs & Benches",
        "price": 10.50,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Includes Velcro Hard-Back Cushion",
        "image": "/images/products/chiavari-chair-with-pad-silver.jpg",
        "image_alt": "Silver Chiavari chair with cushion, available to rent in Atlanta, Georgia",
        "image_w": 441, "image_h": 776,
        "options": [],
        "specs": [
            ("Seat Height", '17.75"H'),
            ("Overall Width", '15.75"W'),
            ("Overall Depth", '18"D'),
            ("Overall Height", '36.25"H'),
            ("Weight Capacity", "500 lbs."),
        ],
        "description": (
            "Introducing our Silver Chiavari Chair: the perfect fusion of elegance and versatility for "
            "your event's seating. With its cool silver finish and classic Chiavari design, this chair "
            "adds a touch of sophistication to any setting. Ideal for weddings, banquets, or upscale "
            "gatherings, its timeless appeal complements a variety of decor styles. Elevate your event's "
            "ambiance and impress your guests with our Silver Chiavari Chair, where comfort meets style "
            "in every seat."
        ),
    },
    {
        "slug": "chiavari-chair-with-pad-mahogany",
        "parent_slug": "chiavari-chair-rentals",
        "parent_name": "Chiavari Chair Rentals Atlanta",
        "name": "Chiavari Chair with Pad - Mahogany",
        "short_name": "Mahogany Chiavari Chair",
        "category": "Chairs & Benches",
        "price": 10.50,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Includes Velcro Hard-Back Cushion",
        "image": "/images/products/chiavari-chair-with-pad-mahogany.jpg",
        "image_alt": "Mahogany Chiavari chairs with ivory cushions set at farm tables for an outdoor wedding reception in Atlanta, Georgia",
        "image_w": 640, "image_h": 426,
        "options": [],
        "specs": [
            ("Seat Height", '17.75"H'),
            ("Overall Width", '15.75"W'),
            ("Overall Depth", '18"D'),
            ("Overall Height", '36.25"H'),
            ("Weight Capacity", "500 lbs."),
        ],
        "description": (
            "Introducing our Mahogany Chiavari Chair: the perfect blend of sophistication and warmth for "
            "your event's seating. With its rich mahogany color and classic Chiavari design, this chair "
            "adds elegance to any setting. Ideal for weddings, banquets, or upscale gatherings, its "
            "timeless appeal complements a variety of decor styles. Elevate your event's ambiance and "
            "impress your guests with our Mahogany Chiavari Chair, where comfort meets style in every seat."
        ),
    },
    {
        "slug": "5-foot-stainless-steel-mobile-bar",
        "parent_slug": "bar-beverage-equipment-rentals",
        "parent_name": "Bar & Beverage Equipment Rentals Atlanta",
        "name": "Bar, 5' Stainless Steel Mobile",
        "short_name": "5' Stainless Steel Mobile Bar",
        "category": "Bar & Beverage Equipment",
        "price": 179.99,
        "unit": "bar",
        "unit_plural": "bars",
        "min_qty": 1,
        "default_qty": 1,
        "delivery_only": True,
        "includes": "Includes ice bin, bottle rail and storage shelving",
        "image": "/images/products/5-foot-stainless-steel-mobile-bar.jpg",
        "image_alt": "5-foot stainless steel mobile bar with ice bin, bottle rail and storage shelving, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [
            ("Length", "5'"),
            ("Material", "Stainless steel"),
        ],
        "description": (
            "Introducing our 5' Stainless Steel Mobile Bar: the pinnacle of versatility and sophistication "
            "for your event. Crafted with sleek stainless steel, this mobile bar is designed to impress "
            "and serve with style. Its compact yet spacious design makes it perfect for weddings, parties, "
            "or corporate functions, while its mobility ensures seamless setup and service anywhere in "
            "your venue."
        ),
    },
    {
        "slug": "contemporary-black-leather-barstool",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Contemporary Black Leather Barstool",
        "short_name": "Black Leather Barstool",
        "category": "Chairs & Benches",
        "price": 25.00,
        "unit": "barstool",
        "unit_plural": "barstools",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Adjustable height, chrome base",
        "image": "/images/products/contemporary-black-leather-barstool.jpg",
        "image_alt": "Contemporary black leather barstool with a chrome adjustable base, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 1078,
        "options": [],
        "specs": [
            ("Seat Height", '31"'),
            ("Seat Depth", '16"'),
            ("Overall Height", '43.5"'),
        ],
        "description": (
            "Introducing our Black Leather Contemporary Barstool: the epitome of modern sophistication "
            "for your event's bar area. With its sleek black leather upholstery and contemporary design, "
            "this barstool adds a touch of elegance to any setting. Perfect for weddings, cocktail "
            "parties, or upscale gatherings, its comfortable seat and adjustable height ensure both "
            "style and functionality. Elevate your event's ambiance and impress your guests with our "
            "Black Leather Contemporary Barstool, where comfort meets chic in every seat."
        ),
    },
    {
        "slug": "30-inch-round-highboy-table",
        "parent_slug": "table-rentals",
        "parent_name": "Table Rentals Atlanta",
        "name": '30" Round Highboy Table',
        "short_name": "30\" Round Highboy Table",
        "category": "Tables",
        "price": 25.00,
        "unit": "table",
        "unit_plural": "tables",
        "min_qty": 1,
        "default_qty": 1,
        "delivery_only": True,
        "includes": "Seats 4 to 5 people standing",
        "image": "/images/products/30-inch-round-highboy-table.jpg",
        "image_alt": "30-inch round highboy cocktail table with chrome base, available to rent in Atlanta, Georgia",
        "image_w": 620, "image_h": 620,
        "options": [],
        "specs": [
            ("Diameter", '30"'),
            ("Seats", "4 to 5 people"),
        ],
        "description": (
            "Introducing our 30\" Round High Boy Table: the versatile and practical addition to your "
            "event's seating arrangements. Designed with durability and convenience in mind, this high "
            "boy table provides a sturdy surface for guests to gather around. Perfect for cocktail "
            "parties, receptions, or networking events, its compact size makes it easy to fit into any "
            "venue. Elevate your event's ambiance and create stylish gathering spaces with our 30\" "
            "Round High Boy Table, where every moment is supported with reliability and functionality."
        ),
    },
    {
        "slug": "child-stacking-chair-14-inch-black",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": 'Child Stacking Chair (14" Seat) - Black',
        "short_name": "Child Stacking Chair",
        "category": "Chairs & Benches",
        "price": 4.50,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "default_qty": 20,
        "delivery_only": True,
        "includes": "Recommended for Grades K–2",
        "image": "/images/products/child-stacking-chair-14-inch-black.jpg",
        "image_alt": "Black children's stacking chair with chrome legs, available to rent in Atlanta, Georgia",
        "image_w": 500, "image_h": 500,
        "options": [],
        "specs": [
            ("Recommended For", "Grades K–2"),
            ("Seat Height", '13.5"H'),
            ("Overall Width", '15.25"W'),
            ("Overall Depth", '19.25"D'),
            ("Overall Height", '24.5"H'),
            ("Weight Capacity", "440 lbs."),
        ],
        "description": (
            "Introducing our Children's Black Stacking Chair: the versatile seating solution for young "
            "guests at your event. With its sleek black design and stackable feature, this chair offers "
            "both style and convenience. Ideal for birthday parties, playdates, or any gathering, its "
            "lightweight construction allows for easy arrangement and storage. Elevate your event's "
            "ambiance and provide comfortable seating for the little ones with our Children's Black "
            "Stacking Chair, where practicality meets modern design in every seat."
        ),
    },
    {
        "slug": "ghost-oval-back-chair",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Ghost Oval Back Chair",
        "short_name": "Ghost Oval Back Chair",
        "category": "Chairs & Benches",
        "price": 17.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Clear acrylic with an oval cutout back",
        "image": "/images/products/ghost-oval-back-chair.jpg",
        "image_alt": "Clear acrylic ghost chair with an oval cutout back, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Introducing our Ghost Oval Back Chair: a clear acrylic chair with a sleek oval cutout back "
            "that adds contemporary polish to any tablescape. Its transparent design blends into any "
            "color scheme, making it a versatile pick for weddings, galas or modern receptions."
        ),
    },
    {
        "slug": "o-back-chair-black",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "O-Back Chair - Black",
        "short_name": "Black O-Back Chair",
        "category": "Chairs & Benches",
        "price": 14.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Black metal frame with a round cutout back",
        "image": "/images/products/o-back-chair-black.jpg",
        "image_alt": "Black metal chair with a round cutout back, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Black O-Back Chair pairs a slim metal frame with a distinctive round cutout in the "
            "seat back for a clean, modern silhouette. A popular choice for cocktail receptions, lounge "
            "seating and contemporary weddings."
        ),
    },
    {
        "slug": "o-back-chair-gold",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "O-Back Chair - Gold",
        "short_name": "Gold O-Back Chair",
        "category": "Chairs & Benches",
        "price": 14.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Gold metal frame with a round cutout back",
        "image": "/images/products/o-back-chair-gold.jpg",
        "image_alt": "Gold metal chair with a round cutout back, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Gold O-Back Chair brings warm metallic shine to a slim frame with a round cutout back, "
            "adding a touch of glamour to receptions, galas and upscale celebrations."
        ),
    },
    {
        "slug": "plastic-folding-chair-black",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Plastic Folding Chair - Black",
        "short_name": "Black Plastic Folding Chair",
        "category": "Chairs & Benches",
        "price": 3.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Lightweight, folds flat for easy delivery",
        "image": "/images/products/plastic-folding-chair-black.jpg",
        "image_alt": "Black plastic folding chair, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Black Plastic Folding Chair is the practical, budget-friendly choice for casual "
            "gatherings, backyard parties and community events. Lightweight and easy to set up, it "
            "folds flat for fast delivery and pickup."
        ),
    },
    {
        "slug": "resin-folding-chair-with-pad-black",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Resin Folding Chair w/Pad - Black",
        "short_name": "Black Resin Folding Chair w/Pad",
        "category": "Chairs & Benches",
        "price": 6.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Includes a cushioned seat pad",
        "image": "/images/products/resin-folding-chair-with-pad-black.jpg",
        "image_alt": "Black resin folding chair with a cushioned seat pad, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Black Resin Folding Chair with Pad combines a durable resin frame with a cushioned "
            "seat for extra comfort during longer events, from ceremonies to banquet-style dinners."
        ),
    },
    {
        "slug": "resin-folding-chair-with-pad-natural-wood",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Resin Folding Chair w/Pad - Natural Wood",
        "short_name": "Natural Wood Resin Folding Chair w/Pad",
        "category": "Chairs & Benches",
        "price": 6.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Includes a cushioned seat pad",
        "image": "/images/products/resin-folding-chair-with-pad-natural-wood.jpg",
        "image_alt": "Natural wood-finish resin folding chair with a cushioned seat pad, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Natural Wood Resin Folding Chair with Pad gives the warm look of wood grain with the "
            "durability of resin, plus a cushioned seat for comfortable extended seating at ceremonies "
            "and receptions."
        ),
    },
    {
        "slug": "resin-folding-chair-with-pad-white",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Resin Folding Chair w/Pad - White",
        "short_name": "White Resin Folding Chair w/Pad",
        "category": "Chairs & Benches",
        "price": 6.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Includes a cushioned seat pad",
        "image": "/images/products/resin-folding-chair-with-pad-white.jpg",
        "image_alt": "White resin folding chair with a cushioned seat pad, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our White Resin Folding Chair with Pad offers a clean, classic look with the comfort of a "
            "cushioned seat, a dependable choice for weddings, ceremonies and formal events."
        ),
    },
    {
        "slug": "veronique-chair-white",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Veronique Chair - White",
        "short_name": "White Veronique Chair",
        "category": "Chairs & Benches",
        "price": 14.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Ornate cut-out back, garden-style look",
        "image": "/images/products/veronique-chair-white.jpg",
        "image_alt": "White Veronique chair with an ornate cut-out back, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our White Veronique Chair features an ornate cut-out back for a romantic, vintage-inspired "
            "look, a popular pairing with farmhouse tables and garden-style wedding decor."
        ),
    },
    {
        "slug": "wishbone-dining-chair-natural-wood",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Wishbone Dining Chair - Natural Wood",
        "short_name": "Natural Wood Wishbone Dining Chair",
        "category": "Chairs & Benches",
        "price": 27.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Woven seat, curved wood back",
        "image": "/images/products/wishbone-dining-chair-natural-wood.jpg",
        "image_alt": "Natural wood wishbone dining chair with a woven seat, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Natural Wood Wishbone Dining Chair brings a mid-century-inspired silhouette with a "
            "woven seat and curved wood back, ideal for intimate dinners, styled shoots and modern "
            "receptions."
        ),
    },
    {
        "slug": "directors-chair-24-inch-counter-height",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": 'Director\'s Chair - 24" Counter Height',
        "short_name": "24\" Counter Height Director's Chair",
        "category": "Chairs & Benches",
        "price": 30.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Folding wood frame with black canvas seat",
        "image": "/images/products/directors-chair-24-inch-counter-height.jpg",
        "image_alt": "Wood-frame director's chair with black canvas seat at counter height, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our 24\" Counter Height Director's Chair pairs a natural wood frame with a black canvas "
            "seat and back for classic, portable seating. Its folding design makes it easy to set up "
            "for film-style photo moments, lounge areas or casual bar-height seating."
        ),
    },
    {
        "slug": "directors-chair-black-24-inch-counter-height",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": 'Director\'s Chair Black - 24" Counter Ht.',
        "short_name": "Black 24\" Counter Height Director's Chair",
        "category": "Chairs & Benches",
        "price": 30.00,
        "unit": "chair",
        "unit_plural": "chairs",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Folding black frame with black canvas seat",
        "image": "/images/products/directors-chair-black-24-inch-counter-height.jpg",
        "image_alt": "All-black director's chair at counter height, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Black 24\" Counter Height Director's Chair offers the same classic folding silhouette "
            "in an all-black finish, a versatile pick for photo booths, greenroom seating or bar-height "
            "lounge areas."
        ),
    },
    {
        "slug": "ghost-clear-barstool",
        "parent_slug": "chair-rentals",
        "parent_name": "Chair Rentals Atlanta",
        "name": "Ghost Clear Barstool",
        "short_name": "Ghost Clear Barstool",
        "category": "Chairs & Benches",
        "price": 28.00,
        "unit": "barstool",
        "unit_plural": "barstools",
        "min_qty": 1,
        "delivery_only": True,
        "includes": "Clear acrylic, bar height",
        "image": "/images/products/ghost-clear-barstool.jpg",
        "image_alt": "Clear acrylic ghost barstool, available to rent in Atlanta, Georgia",
        "image_w": 640, "image_h": 640,
        "options": [],
        "specs": [],
        "description": (
            "Our Ghost Clear Barstool brings the same transparent, modern look as our ghost chairs to "
            "bar-height seating, a sleek pick for cocktail receptions, high-top tables and modern bar "
            "setups."
        ),
    },
]

PRODUCTS_BY_PARENT = {}
for _p in PRODUCTS:
    PRODUCTS_BY_PARENT.setdefault(_p["parent_slug"], []).append(_p)


def product_href(p):
    return f'/services/{p["parent_slug"]}/{p["slug"]}/'


def service_family_groups(families):
    """{slug: [fam, ...]} — every family (core service page, specialty page,
    or tag/variant family like Chair/Tent/Table Rentals) grouped under the
    core SERVICES slug it belongs to, plus 'specialty' and 'seasonal' keys
    for families that attach to a specialty page or neither. Shared by
    build_services_index() and build_index() (homepage) so both agree on
    exactly which city/service pages exist and where they nest."""
    active = {fam["url_prefix"]: fam for fam in families
              if fam["url_prefix"] != CITY_HUB_FAMILY_PREFIX and fam["entries"]}
    core_prefixes = set(SERVICES)
    specialty_prefixes = {slug for slug, _ in SPECIALTY_SLUGS}

    groups = {"specialty": {}, "seasonal": []}
    for prefix, fam in active.items():
        if prefix in core_prefixes:
            groups.setdefault(prefix, []).insert(0, fam)
        elif prefix in specialty_prefixes:
            groups["specialty"].setdefault(prefix, []).insert(0, fam)

    for prefix, fam in active.items():
        if prefix in core_prefixes or prefix in specialty_prefixes:
            continue
        if fam["match_mode"] == "theme" or not fam["slug"]:
            groups["seasonal"].append(fam)
        else:
            groups.setdefault(fam["slug"], []).append(fam)

    for key in list(groups):
        if key in ("specialty", "seasonal"):
            continue
        groups[key].sort(key=lambda f: (f["match_mode"] == "tag", f["name"]))
    groups["seasonal"].sort(key=lambda f: f["name"])
    return groups


def city_links_html(fam, heading=None):
    links = "\n            ".join(
        f'<li><a href="{city_service_href(fam["url_prefix"], loc["slug"])}">{esc(loc["name"])}</a> '
        f'<span class="muted">({len(matched)})</span></li>'
        for loc, matched, _ in fam["entries"])
    return f'''
        <div class="svc-city-links">
          <p class="svc-city-links-label">{esc(heading or fam["name"])} by city:</p>
          <ul class="bullet-services svc-city-cols">
            {links}
          </ul>
        </div>'''


def build_services_index(providers, families):
    """/services/ hub — every core + specialty service page (regardless of
    current provider count, so a page never silently disappears from the hub
    just because it has zero live listings right now), each collapsible with
    its city/service pages nested underneath."""
    counts = {s: sum(1 for p in providers if s in p["services"]) for s in SERVICES}
    groups = service_family_groups(families)

    def blocks_for(fams, skip_heading_slug=None):
        return "".join(
            city_links_html(fam, None if fam["url_prefix"] == skip_heading_slug else fam["name"])
            for fam in fams)

    items = "\n      ".join(
        f'''<details class="svc-collapsible">
        <summary><span>{SERVICES[s]} in Atlanta Georgia</span>'''
        + (f'<span class="muted">{counts[s]} provider{"s" if counts[s] != 1 else ""}</span>' if counts[s] else "")
        + f'''</summary>
        <div class="svc-collapsible-body">
          {blocks_for(groups.get(s, []), skip_heading_slug=s)}
          <p><a href="/services/{s}/">View {SERVICES[s]} details &rsaquo;</a></p>
        </div>
      </details>'''
        for s in SERVICES)
    specialty_items = "\n      ".join(
        f'''<details class="svc-collapsible">
        <summary><span>{name}</span></summary>
        <div class="svc-collapsible-body">
          {blocks_for(groups["specialty"].get(slug, []), skip_heading_slug=slug)}
          <p><a href="/services/{slug}/">View {esc(name)} details &rsaquo;</a></p>
        </div>
      </details>'''
        for slug, name in SPECIALTY_SLUGS)

    seasonal_html = ""
    if groups["seasonal"]:
        seasonal_items = "\n      ".join(
            f'''<details class="svc-collapsible">
        <summary><span>{esc(fam["name"])}</span></summary>
        <div class="svc-collapsible-body">
          {city_links_html(fam)}
          <p><a href="/find/{fam["url_prefix"]}-near-me/">View {esc(fam["name"])} near me &rsaquo;</a></p>
        </div>
      </details>'''
            for fam in groups["seasonal"])
        seasonal_html = f'''
    <h2>Seasonal &amp; Themed Party Rentals</h2>
    <div class="svc-collapsible-list">
      {seasonal_items}
    </div>'''
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
    <div class="svc-collapsible-list">
      {items}
    </div>
    <h2>Specialty Rental Equipment</h2>
    <p>Deep-dive pages for specific event equipment popular at Atlanta weddings, corporate events and parties:</p>
    <div class="svc-collapsible-list">
      {specialty_items}
    </div>
    {seasonal_html}
    <div class="callout">
      <p><strong>Not sure what you need?</strong> Use the Free Instant Quote wizard and tell us about your event — we'll match you with the right Atlanta providers and equipment for your date.</p>
    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Get a Free Atlanta Bounce House Quote</h2>
    <p>Tell us about your event and we'll match you with available Atlanta providers in minutes.</p>
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
             f"<p>Click <a href=\"#\" data-wizard-open>Free Instant Quote</a> to tell us about your event. We'll match you with available Atlanta providers that offer {nml} for your date.</p>"),
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

        city_filter_options = "\n        ".join(
            f'<option value="{esc(c)}">{esc(c)}</option>'
            for c in sorted(set(p["city"] for p in offering)))
        listicle = listicle_section_html(
            offering, "provider", "providers", "city",
            "City", city_filter_options,
            searchmap_html(area="Atlanta", zoom=10, service=SERVICES_SHORT[slug]), f"lc-svc-{slug}")

        page = head(f'{s["name"]} In Atlanta Georgia', s["intro"][:155].replace('"', "'"),
                    f"{DOMAIN}/services/{slug}/", extra)
        page += header("services") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/services/">Services</a> &rsaquo; {s["name"]}</div>
    <h1>{len(offering)} {s["name"]} Providers in Atlanta, GA</h1>
    <p>{s["intro"]}</p>
  </div>
</div>

<section>
  <div class="container">
    {listicle}
  </div>
</section>

<section class="alt">
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
          <a class="btn btn-block" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/wizard.js"></script>
{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/listicle.js"></script>
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
            "meta_desc": "Chiavari chair rentals in Atlanta, Georgia for weddings, galas and corporate events. Compare local providers, view pricing and get a free quote. Call 404-737-1843.",
            "intro": "Chiavari chair rentals in Atlanta, Georgia are the gold standard for elegant event seating. These lightweight, stackable resin and wood chairs are a fixture at Atlanta weddings, fundraising galas and corporate awards dinners.",
            "body": [
                "Chiavari chairs originated in Chiavari, Italy and have become the most requested formal chair rental in Atlanta. Available in gold, silver, white, black and mahogany finishes, they pair with almost any linen color and event theme. Their slim profile allows more seating per square foot than traditional banquet chairs, making them ideal for Atlanta ballrooms, estate gardens and tent events.",
                "Atlanta rental providers typically include cushions in ivory, black or champagne at no extra charge with chiavari chair orders. Minimum order quantities start around 50 chairs for most providers, with delivery, setup and pickup included in the quoted price. Book 4 to 6 weeks ahead for spring wedding season when demand peaks across the metro."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            # Real per-chair pricing now lives on the product-request pages
            # linked above (Rent Direct From Us), so the old estimate ranges
            # would just be confusing/redundant on this page.
            "hide_price_tiers": True,
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
                ("How far in advance should I book a throne chair rental?", "Book throne chairs 4 to 8 weeks ahead for spring and fall wedding season. Saturday dates in April, May, September and October fill fastest. Call 404-737-1843 to check current availability."),
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
        {
            "slug": "bar-beverage-equipment-rentals",
            "name": "Bar & Beverage Equipment Rentals Atlanta",
            "h1": "Bar & Beverage Equipment Rentals in Atlanta Georgia",
            "meta_desc": "Bar and beverage equipment rentals in Atlanta, Georgia — portable bars, beverage dispensers, ice tubs and glassware for weddings, corporate events and parties. Free quote.",
            "intro": "Bar and beverage equipment rentals in Atlanta, Georgia turn any backyard, tent or venue into a fully stocked bar. From a single portable bar station to a full setup with dispensers, ice tubs and glassware, Atlanta providers can outfit an event of any size.",
            "body": [
                "A rental bar setup typically starts with a portable bar unit — a freestanding wood, resin or acrylic bar front that a bartender works behind. Around it, most Atlanta providers offer beverage dispensers for iced tea, lemonade and infused water, insulated ice tubs and coolers for bottled and canned drinks, and glassware or disposable drinkware sized to your guest count. Beer and wine tubs, cocktail shaker kits and portable draft/kegerator units are common add-ons for weddings and corporate happy hours.",
                "Most bar and beverage equipment rents by the piece or as a bundled package, and pairs naturally with a cocktail table order for a complete bar area. Atlanta providers typically deliver, set up and break down the equipment; ice, beverages and bartending staff are usually arranged separately unless you book a full-service package. Reserve bar equipment 2 to 4 weeks ahead for weekend weddings and corporate events during peak spring and fall season."
            ],
            "parent_slug": "concession-rentals",
            "parent_name": "Concession Rentals",
            "price_tiers": [
                {"tier": "Basic Setup", "amount": "$60&ndash;$120", "sub": "/ bar unit", "items": ["One portable bar front", "Delivery within Atlanta", "Setup and pickup", "Pairs with cocktail tables"]},
                {"tier": "Standard Package", "amount": "$150&ndash;$300", "sub": "/ event", "items": ["Bar unit + dispensers", "Ice tubs and coolers", "Metro Atlanta delivery", "Glassware add-on available"]},
                {"tier": "Full Bar Package", "amount": "$350&ndash;$700+", "sub": "/ event", "items": ["Multiple bar stations", "Dispensers, tubs and glassware", "Extended delivery radius", "Coordinated with staffing add-on"]},
            ],
            "faqs": [
                ("How much does bar equipment rental cost in Atlanta?", "A single portable bar unit runs about $60 to $120. A standard package with dispensers and ice tubs is $150 to $300, and a full multi-station bar package with glassware runs $350 to $700+. Delivery is typically included within metro Atlanta."),
                ("Does bar equipment rental include a bartender?", "Not by default. Most Atlanta providers rent the physical equipment only; bartending and serving staff are booked separately through our Party Entertainment and Staff Rentals page or as an add-on with select providers."),
                ("Can I rent just a beverage dispenser without a full bar?", "Yes. Beverage dispensers, ice tubs and glassware can all be rented individually without a portable bar unit — a good fit for casual parties, school events or offices that just need a self-serve drink station."),
            ],
        },
        {
            "slug": "chair-rentals",
            "name": "Chair Rentals Atlanta",
            "h1": "Chair Rentals in Atlanta Georgia",
            "meta_desc": "Chair rentals in Atlanta, Georgia for weddings, parties, schools and corporate events. Chiavari, folding, child-size and stacking chairs delivered and set up. Free quote.",
            "intro": "Chair rentals in Atlanta, Georgia cover everything from elegant chiavari seating for weddings to child-size stacking chairs for school events and birthday parties. Whatever the guest count and whatever the age group, there's a chair that fits the event.",
            "body": [
                "Seating is usually the single largest line item in an event rental order, so getting the chair style and count right matters. Standard white or black folding chairs are the workhorse choice for backyard parties, graduations and church events. Chiavari chairs — available in gold, mahogany, clear ghost and other finishes — are the go-to for weddings and upscale receptions where the seating is part of the decor. For children's events, school programs and daycare functions, child-size stacking chairs sized to grades K–2 keep young guests comfortable and safe.",
                "Plan roughly one chair per confirmed guest, plus a small buffer for last-minute additions. Most Atlanta providers deliver, set up and collect chairs as part of the rental price, and chairs bundle easily with tables, linens and tents in a single order. Some items on this page we stock and deliver ourselves at a flat per-chair rate — pick your exact quantity and request delivery directly, no back-and-forth quoting."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Child / Stacking", "amount": "$4&ndash;$7", "sub": "/ chair", "items": ["Child-size stacking chairs", "Sized for grades K&ndash;2", "Delivery within Atlanta", "Setup and pickup"]},
                {"tier": "Folding Chairs", "amount": "$2&ndash;$5", "sub": "/ chair", "items": ["White, black or resin folding", "Indoor or outdoor rated", "Metro Atlanta delivery", "Volume pricing available"]},
                {"tier": "Chiavari Chairs", "amount": "$8&ndash;$12", "sub": "/ chair", "items": ["Gold, mahogany or clear ghost", "Cushion included", "Full setup service", "Wedding &amp; gala ready"]},
            ],
            "faqs": [
                ("How much do chair rentals cost in Atlanta?", "It depends on the style. Folding chairs run about $2 to $5 each, child-size stacking chairs about $4 to $7 each, and chiavari chairs about $8 to $12 each. Delivery is typically included within metro Atlanta. Items we stock ourselves show their exact per-chair rate on this page."),
                ("What size chairs do you have for children?", "Our child stacking chairs have a 13.5-inch seat height and are recommended for grades K through 2. They stack for easy transport and setup, making them a good fit for school events, daycare functions and children's birthday parties."),
                ("How many chairs should I rent for my event?", "Plan for one chair per confirmed guest, plus about 5 percent extra for last-minute additions. If you're running separate ceremony and reception areas, confirm whether chairs will be moved between them or whether you need two full sets."),
            ],
        },
        {
            "slug": "table-rentals",
            "name": "Table Rentals Atlanta",
            "h1": "Table Rentals in Atlanta Georgia",
            "meta_desc": "Table rentals in Atlanta, Georgia for weddings, parties, corporate events and school functions. Round, banquet, farmhouse and cocktail tables delivered and set up. Free quote.",
            "intro": "Table rentals in Atlanta, Georgia cover every shape and size an event needs — round tables for a seated dinner, long banquet tables for a buffet line, rustic farmhouse tables for a wedding reception and cocktail tables for a standing reception.",
            "body": [
                "Round tables (typically 60&quot; or 72&quot; across) are the standard for seated dinners and seat 8 to 10 guests each. Rectangular banquet tables (6&#39; or 8&#39; long) work well for buffet lines, registration areas and casual gatherings, and stack easily for delivery. Rustic wood farmhouse tables have become the centerpiece choice for outdoor and barn-style wedding receptions, often left bare to show the wood grain rather than fully linened. Round cocktail tables (30&quot; high-top) anchor a standing reception or bar area and pair naturally with barstools.",
                "Plan on one round table per 8 to 10 seated guests, or roughly 6 linear feet of banquet table per 8 guests along a buffet line. Most Atlanta providers deliver, set up and collect tables as part of the rental price, and tables bundle easily with chairs, linens and tents in a single order. Some items on this page we stock and deliver ourselves at a flat per-table rate — pick your exact quantity and request delivery directly, no back-and-forth quoting."
            ],
            "parent_slug": "tents-tables-and-chair-rentals",
            "parent_name": "Tents, Tables and Chair Rentals",
            "price_tiers": [
                {"tier": "Cocktail Tables", "amount": "$8&ndash;$22", "sub": "/ table", "items": ["30&quot; high-top round", "With or without linen", "Delivery within Atlanta", "Setup and pickup"]},
                {"tier": "Round &amp; Banquet", "amount": "$10&ndash;$20", "sub": "/ table", "items": ["60&quot;/72&quot; round or 6&#39;/8&#39; banquet", "Seats 8&ndash;10 guests", "Metro Atlanta delivery", "Volume pricing available"]},
                {"tier": "Farmhouse Tables", "amount": "$55&ndash;$130", "sub": "/ table", "items": ["Rustic wood harvest-style", "Seats 8&ndash;10 guests", "Full setup service", "Wedding &amp; reception ready"]},
            ],
            "faqs": [
                ("How much do table rentals cost in Atlanta?", "It depends on the style. Round and banquet tables run about $10 to $20 each, cocktail tables about $8 to $22 each, and rustic farmhouse tables about $55 to $130 each. Delivery is typically included within metro Atlanta. Items we stock ourselves show their exact per-table rate on this page."),
                ("How many guests fit at each table size?", "A 60&quot; round table seats 8 guests comfortably, a 72&quot; round seats 10. An 8&#39; banquet table seats 8 to 10 depending on chair spacing. Cocktail tables are typically used standing, for 3 to 4 guests per table."),
                ("How many tables should I rent for my event?", "Plan for one round table per 8 to 10 seated guests, or about 6 linear feet of banquet table per 8 guests for a buffet setup. Add a few cocktail tables near the bar or entrance for a mixed seated-and-standing layout."),
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

        price_section_html = "" if pg.get("hide_price_tiers") else (
            f'<h2>{pg["name"]} Price Estimates in Atlanta</h2>\n'
            f'        <p>Below are typical Atlanta price ranges. Final pricing depends on the date, delivery distance, rental duration and add-ons. Request a free quote for an exact figure.</p>\n'
            f'        <div class="price-grid">\n          {prices_html}\n        </div>'
        )

        body_html = "\n        ".join(f"<p>{p}</p>" for p in pg["body"])

        # Items we stock and fulfil ourselves at a fixed per-unit rate get a
        # product-request page; surface them prominently above the directory
        # content since they're the one thing on this page you can order
        # directly rather than being matched out to a provider.
        own_products = PRODUCTS_BY_PARENT.get(slug, [])
        products_html = ""
        if own_products:
            def card_media(prod):
                if prod.get("image") and os.path.exists(os.path.join(ROOT, prod["image"].lstrip("/"))):
                    return (f'<img src="{prod["image"]}" alt="{esc(prod["image_alt"])}" '
                            f'width="{prod["image_w"]}" height="{prod["image_h"]}" loading="lazy">')
                return (f'<div class="prod-card-placeholder" role="img" '
                        f'aria-label="{esc(prod["name"])} photo coming soon">{esc(prod["short_name"])}</div>')

            cards = "\n          ".join(
                f'''<a class="prod-card" href="{product_href(prod)}">
            {card_media(prod)}
            <div class="prod-card-body">
              <h3>{esc(prod["name"])}</h3>
              <p class="prod-card-price"><strong>${prod["price"]:.2f}</strong> <span class="muted">per {esc(prod["unit"])}</span></p>
              <p class="muted">{esc(prod["includes"])}</p>
              <span class="prod-card-cta">Pick your quantity &rsaquo;</span>
            </div>
          </a>''' for prod in own_products)
            products_html = f'''
        <h2>Rent Direct From Us</h2>
        <p>We stock and deliver these {pg["parent_name"].lower()} ourselves at a flat per-unit rate &mdash; choose your exact quantity and request delivery in under a minute.</p>
        <div class="prod-card-grid">
          {cards}
        </div>
'''

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
        {products_html}
        <h2>About {pg["name"]} in Atlanta</h2>
        {featured_image_html(slug, alt_override=f'{pg["name"]} set up for an event in Atlanta, Georgia')}
        {body_html}

        <div class="callout">
          <p><strong>Serving all of metro Atlanta.</strong> Providers in our directory deliver {pg["name"].lower()} to Atlanta, Buckhead, Midtown, Decatur, Sandy Springs, Marietta, Roswell and surrounding Georgia communities.</p>
        </div>

        {price_section_html}

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
          <a class="btn btn-block" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        d = os.path.join(ROOT, "services", slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(page)


# ----------------------------------------------------------------- product pages
def build_product_pages():
    """One product-request page per PRODUCTS entry, at
    /services/{parent_slug}/{slug}/. Quantity picker + live running total +
    an order form that posts straight into the Supabase leads table
    (js/product.js) with everything needed to invoice and fulfil the order."""
    urls = []
    for p in PRODUCTS:
        price = p["price"]
        default_qty = p.get("default_qty", max(p["min_qty"], 50))
        opts_html = "\n        ".join(
            f'''<div class="pr-option">
          <label for="opt-{o["key"]}">{esc(o["label"])}</label>
          <select id="opt-{o["key"]}" name="{o["key"]}" data-product-option>
            {"".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in o["choices"])}
          </select>
        </div>''' for o in p["options"])

        specs_html = "\n          ".join(
            f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k, v in p["specs"])
        specs_section_html = (
            f'<h2>Specifications</h2>\n      <table class="pr-specs">\n        <tbody>\n          {specs_html}\n        </tbody>\n      </table>'
            if p["specs"] else "")

        # Render the real photo when the file is actually on disk; otherwise a
        # neutral placeholder, so a product page is never broken by a missing
        # image and starts showing the photo automatically once it's added.
        if p.get("image") and os.path.exists(os.path.join(ROOT, p["image"].lstrip("/"))):
            media_html = (f'<img src="{p["image"]}" alt="{esc(p["image_alt"])}" '
                          f'width="{p["image_w"]}" height="{p["image_h"]}">')
        else:
            media_html = (f'<div class="pr-media-placeholder" role="img" '
                          f'aria-label="{esc(p["name"])} photo coming soon">'
                          f'<span>{esc(p["short_name"])}</span><small>Photo coming soon</small></div>')

        badge = '<span class="pr-badge">Delivery<br>Item Only</span>' if p["delivery_only"] else ""
        delivery_note = ("<li>This is a <strong>delivery only</strong> item &mdash; we drop off and pick up, no setup included.</li>"
                         if p["delivery_only"] else "")

        prod_ld = {
            "@context": "https://schema.org", "@type": "Product",
            "name": p["name"], "category": p["category"],
            "image": DOMAIN + p["image"], "description": p["description"],
            "sku": p["slug"],
            "offers": {"@type": "Offer", "priceCurrency": "USD", "price": f"{price:.2f}",
                       "availability": "https://schema.org/InStock",
                       "url": DOMAIN + product_href(p),
                       "seller": {"@type": "Organization", "name": "Atlanta Bounce House Rentals"}},
        }
        bc_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Services", "item": DOMAIN + "/services/"},
            {"@type": "ListItem", "position": 3, "name": p["parent_name"],
             "item": f'{DOMAIN}/services/{p["parent_slug"]}/'},
            {"@type": "ListItem", "position": 4, "name": p["name"], "item": DOMAIN + product_href(p)}]}
        extra = (f'<script type="application/ld+json">\n{json.dumps(prod_ld, ensure_ascii=False)}\n</script>\n'
                 f'<script type="application/ld+json">\n{json.dumps(bc_ld, ensure_ascii=False)}\n</script>\n')

        title = f'{p["name"]} Rental Atlanta | ${price:.2f} per {p["unit"]}'
        desc = (f'Rent {p["name"]} in Atlanta, Georgia for ${price:.2f} per {p["unit"]}. '
                f'Pick your exact quantity and request delivery — free quote, fast response.')

        page = head(esc(title), desc, DOMAIN + product_href(p), extra)
        page += header("services") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/services/">Services</a> &rsaquo; <a href="/services/{p["parent_slug"]}/">{esc(p["parent_name"])}</a> &rsaquo; {esc(p["name"])}</div>
    <h1>{esc(p["name"])}</h1>
    <p class="muted">Category: {esc(p["category"])}</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="pr-layout"
      data-product
      data-product-name="{esc(p["name"])}"
      data-product-slug="{esc(p["slug"])}"
      data-product-price="{price}"
      data-product-unit="{esc(p["unit"])}"
      data-product-unit-plural="{esc(p["unit_plural"])}"
      data-product-min="{p["min_qty"]}"
      data-product-delivery-fee="{PRODUCT_DELIVERY_FEE}">

      <div class="pr-media">
        {media_html}
        {badge}
      </div>

      <div class="pr-buy">
        <p class="pr-includes">{esc(p["includes"])}</p>
        <div class="pr-price"><strong>${price:.2f}</strong> <span class="muted">per {esc(p["unit"])}</span></div>

        {opts_html}

        <div class="pr-option">
          <label for="pr-qty">Number of {esc(p["unit_plural"])}</label>
          <div class="pr-qty-row">
            <button type="button" class="pr-qty-btn" data-qty-step="-1" aria-label="Decrease quantity">&minus;</button>
            <input id="pr-qty" type="number" min="{p["min_qty"]}" step="1" value="{default_qty}" inputmode="numeric" data-qty>
            <button type="button" class="pr-qty-btn" data-qty-step="1" aria-label="Increase quantity">+</button>
          </div>
        </div>

        <p class="pr-total-note muted" data-total-note></p>
        <div class="pr-total-row">
          <span>+ Standard delivery fee</span>
          <span>${PRODUCT_DELIVERY_FEE:,.2f}</span>
        </div>
        <div class="pr-total">
          <span>Estimated total</span>
          <strong data-total></strong>
        </div>

        <a class="btn btn-block" href="#request">Request These {esc(p["unit_plural"].title())} &rsaquo;</a>
        <p class="muted" style="font-size:0.84rem;margin-top:10px;">This isn't a charge &mdash; it sends us your request, and we confirm availability and the final invoice before anything is due.</p>
      </div>
    </div>

    <div class="content" style="margin-top:40px;">
      <h2>About the {esc(p["short_name"])}</h2>
      <p>{esc(p["description"])}</p>

      {specs_section_html}
      <ul>
        {delivery_note}
        <li>{esc(p["includes"])}.</li>
        <li>Rental rate is <strong>${price:.2f} per {esc(p["unit"])}</strong>, plus a flat <strong>${PRODUCT_DELIVERY_FEE:,.2f} standard delivery fee</strong> per order.</li>
      </ul>

      <h2>Delivery &amp; Pickup</h2>
      <p>Delivery is <strong>drop-off and pickup only</strong> &mdash; we don't set anything up. A flat ${PRODUCT_DELIVERY_FEE:,.2f} covers standard delivery and pickup for your order.</p>
      <table class="pr-specs">
        <tbody>
          {"".join(f'<tr><th>{esc(label)}</th><td>{window_txt}</td></tr>' for label, window_txt in PRODUCT_DELIVERY_POLICY["hours"])}
        </tbody>
      </table>
      <ul>
        {"".join(f'<li>{item}</li>' for item in PRODUCT_DELIVERY_POLICY["included"])}
      </ul>
    </div>
  </div>
</section>

<section class="alt" id="request">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Request This Item</div>
      <h2>Request Your {esc(p["short_name"])}s</h2>
      <p>Tell us where and when you need them. We'll confirm availability and send an invoice &mdash; nothing is charged from this form.</p>
    </div>

    <form class="pr-form" data-product-form novalidate>
      <div data-pr-success class="form-success" style="display:none;">
        <strong>Request received.</strong> We'll confirm availability and send your invoice shortly. For anything urgent, call or text <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a>.
      </div>
      <div data-pr-error class="form-success" style="display:none;background:#fdeaea;border-color:#f3c2c2;color:#a12626;"></div>

      <div data-pr-fields>
        <div class="pr-summary-bar">
          <span data-form-summary></span>
          <strong data-form-total></strong>
        </div>

        <h3>Your details</h3>
        <div class="pr-grid">
          <div class="field"><label for="pr-name">Full name <span class="req">*</span></label><input id="pr-name" name="name" type="text" autocomplete="name" required></div>
          <div class="field"><label for="pr-company">Company / organization</label><input id="pr-company" name="company" type="text" autocomplete="organization"></div>
          <div class="field"><label for="pr-phone">Phone <span class="req">*</span></label><input id="pr-phone" name="phone" type="tel" autocomplete="tel" required></div>
          <div class="field"><label for="pr-email">Email <span class="req">*</span></label><input id="pr-email" name="email" type="email" autocomplete="email" required></div>
        </div>

        <h3>Delivery details</h3>
        <div class="pr-grid">
          <div class="field pr-span2"><label for="pr-venue">Venue name</label><input id="pr-venue" name="venue_name" type="text" placeholder="e.g. Summerour Studio"></div>
          <div class="field pr-span2"><label for="pr-address">Delivery street address <span class="req">*</span></label><input id="pr-address" name="delivery_address" type="text" autocomplete="street-address" required></div>
          <div class="field"><label for="pr-city">City <span class="req">*</span></label><input id="pr-city" name="delivery_city" type="text" autocomplete="address-level2" required></div>
          <div class="field"><label for="pr-state">State</label><input id="pr-state" name="delivery_state" type="text" value="GA" autocomplete="address-level1"></div>
          <div class="field"><label for="pr-zip">ZIP code <span class="req">*</span></label><input id="pr-zip" name="zip_code" type="text" inputmode="numeric" autocomplete="postal-code" required></div>
        </div>

        <h3>Dates</h3>
        <div class="pr-grid">
          <div class="field"><label for="pr-delivery-date">Delivery date <span class="req">*</span></label><input id="pr-delivery-date" name="delivery_date" type="date" required></div>
          <div class="field"><label for="pr-delivery-time">Preferred delivery time</label><input id="pr-delivery-time" name="delivery_time" type="time"></div>
          <div class="field"><label for="pr-pickup-date">Pickup date</label><input id="pr-pickup-date" name="pickup_date" type="date"></div>
        </div>

        <div class="field"><label for="pr-message">Anything else we should know?</label><textarea id="pr-message" name="message" rows="4" placeholder="Setup location, stairs/elevator access, gate codes, timing constraints&hellip;"></textarea></div>

        <button class="btn btn-block" type="submit" data-pr-submit>Send My Request</button>
        <p class="form-note">Or call/text <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a>. We reply fast &mdash; usually within the hour during business hours.</p>
      </div>
    </form>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Questions About {esc(p["short_name"])} Rentals?</h2>
    <p>Call or text and we'll walk you through quantities, delivery windows and pricing for your event.</p>
    <a class="btn" href="tel:{PHONE_HREF}">Call {PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/product.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        d = os.path.join(ROOT, "services", p["parent_slug"], p["slug"])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(page)
        urls.append(product_href(p))
    return urls


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
        "Browse bounce houses available for rent across Atlanta, Georgia. Classic castles, rainbow combos and more — setup and teardown included. Call 404-737-1843 for pricing and availability.",
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
            f'Rent the {it["name"]} in Atlanta, Georgia. {it["tagline"]} Starting at ${it["pricing"][0]["price"]}. Call 404-737-1843 or request a quote.',
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
          <a class="btn btn-block" href="#" data-wizard-open style="margin-bottom:14px;">Free Instant Quote &rsaquo;</a>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
          <a class="btn btn-block" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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


# ----------------------------------------------------------------- /cities/ listicle hub
def build_cities(providers):
    """/cities/ hub + one listicle page per city with an actual matched
    listing (by ZIP) — same never-show-0 rule as the rest of the site."""
    entries = []
    for loc in LOCATIONS:
        matched = providers_for_location(loc, providers, limit=200)
        if matched:
            entries.append((loc, matched))
    entries.sort(key=lambda e: e[0]["name"])

    cards_html = "\n".join(
        f'''    <a class="loc-card" href="/cities/{loc["slug"]}/">
      <h3>{esc(loc["name"])}</h3>
      <p class="loc-card-meta">{len(matched)} listing{"s" if len(matched) != 1 else ""}</p>
    </a>''' for loc, matched in entries)

    item_ld = {"@context": "https://schema.org", "@type": "ItemList",
               "itemListElement": [
                   {"@type": "ListItem", "position": i + 1, "name": loc["name"],
                    "url": f'{DOMAIN}/cities/{loc["slug"]}/'}
                   for i, (loc, matched) in enumerate(entries)]}
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
        {"@type": "ListItem", "position": 2, "name": "Cities", "item": DOMAIN + "/cities/"}]}
    extra = (f'<script type="application/ld+json">\n{json.dumps(item_ld, ensure_ascii=False)}\n</script>\n'
             f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n')

    hub = head(
        "Bounce House & Party Rental Providers by City in Atlanta, Georgia",
        f"Browse {len(entries)} Atlanta-area cities with bounce house and party rental providers. See how many listings we track in each city.",
        DOMAIN + "/cities/", extra)
    hub += header("cities") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Cities</div>
    <h1>Bounce House &amp; Party Rental Providers by City</h1>
    <p>Every city we track providers in across metro Atlanta, Georgia. Pick your city to see every business listed there, ranked by rating and review volume.</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="loc-grid">
{cards_html}
    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Don't See Your City?</h2>
    <p>Tell us about your event and we'll match you with an available Atlanta-area provider. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "cities")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(hub)

    for loc, matched in entries:
        nl = loc["name"]
        clat, clng = location_center(loc, providers)
        filter_options = "\n        ".join(
            f'<option value="{s}">{SERVICES[s]}</option>' for s in SERVICES)
        listicle = listicle_section_html(
            matched, "listing", "listings", "business",
            "Service", filter_options,
            searchmap_html(area=nl, lat=clat, lng=clng, zoom=12), "lc-city")

        bc2 = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Cities", "item": DOMAIN + "/cities/"},
            {"@type": "ListItem", "position": 3, "name": nl, "item": f"{DOMAIN}/cities/{loc['slug']}/"}]}
        svc_ld = {"@context": "https://schema.org", "@type": "ItemList",
                  "itemListElement": [
                      {"@type": "ListItem", "position": i + 1,
                       "item": {"@type": "LocalBusiness", "name": p["name"], "url": f'{DOMAIN}/partners/{p["slug"]}/'}}
                      for i, p in enumerate(matched)]}
        extra2 = (f'<script type="application/ld+json">\n{json.dumps(bc2, ensure_ascii=False)}\n</script>\n'
                  f'<script type="application/ld+json">\n{json.dumps(svc_ld, ensure_ascii=False)}\n</script>\n{LEAFLET_HEAD}')

        title = f"{len(matched)} Party Rental Providers in {nl}, GA"
        desc = f"Every party rental provider we track in {nl}, Georgia, ranked by rating and review volume. Search by name or filter by service."

        svc_pages = CITY_SERVICE_INDEX.get(loc["slug"], [])
        svc_pages_html = ""
        if svc_pages:
            svc_links = "\n          ".join(
                f'<li><a href="{city_service_href(up, loc["slug"])}">{esc(nm)}</a> '
                f'<span class="muted">({n} provider{"s" if n != 1 else ""})</span></li>'
                for up, nm, n in svc_pages)
            svc_pages_html = f'''
<section class="alt">
  <div class="container">
    <div class="section-head">
      <h2>{esc(nl)} Rentals by Service</h2>
      <p>Narrow the list above to one specific service in {esc(nl)}.</p>
    </div>
    <ul class="bullet-services">
          {svc_links}
    </ul>
  </div>
</section>'''

        page = head(title, desc, f"{DOMAIN}/cities/{loc['slug']}/", extra2)
        page += header("cities") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/cities/">Cities</a> &rsaquo; {esc(nl)}</div>
    <h1>{title}</h1>
    <p>Every party rental provider we track in {esc(nl)}, ranked by rating and review volume. Search by name, or filter by service. Always confirm hours before you head out.</p>
  </div>
</div>

<section>
  <div class="container">
    {listicle}
    <p style="margin-top:26px;"><a href="/cities/">&larr; All cities</a></p>
  </div>
</section>
{svc_pages_html}

<section class="cta-band">
  <div class="container">
    <h2>Book a Provider in {esc(nl)} Today</h2>
    <p>Tell us about your event and we'll match you with an available {esc(nl)} provider. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/listicle.js"></script>
<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
        cd = os.path.join(ROOT, "cities", loc["slug"])
        os.makedirs(cd, exist_ok=True)
        open(os.path.join(cd, "index.html"), "w").write(page)

    return ["/cities/"] + [f"/cities/{loc['slug']}/" for loc, _ in entries]


def build_find_pages(providers, families):
    """City+service pages at /cities/{city}/{service}/ plus the metro-wide
    "near me" pages and hub that still live under /find/. Generated only for
    cities with an actual matched listing. Page layout is 1) the filtered
    search map, 2) SEO content below it."""
    d = os.path.join(ROOT, "find")
    os.makedirs(d, exist_ok=True)

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
        {"title": f'{fam["name"]} in {loc["name"]}, GA', "url": city_service_href(fam["url_prefix"], loc["slug"])}
        for fam in families for loc, matched, url_slug in fam["entries"]
    ] + [
        {"title": f'{nm["name"]} Near Me', "url": f'/find/{nm["url_slug"]}/'}
        for nm in near_me
    ]

    # --- per-city landing pages (/cities/{city}/{service}/) ---
    for fam in families:
        # The city-hub family's content is the /cities/{city}/ page itself,
        # built by build_cities() — nothing to generate here.
        if fam["url_prefix"] == CITY_HUB_FAMILY_PREFIX:
            continue
        slug = fam["slug"]
        match_mode = fam["match_mode"]
        svc_name = fam["name"]
        svc_short = fam.get("map_filter") or (SERVICES_SHORT.get(slug, "") if slug else "")
        for loc, matched, url_slug in fam["entries"]:
            page_url = city_service_href(fam["url_prefix"], loc["slug"])
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
                     f"<p>Click <a href=\"#\" data-wizard-open>Free Instant Quote</a> to tell us about your event and we'll match you with an available {nl} provider for your date.</p>"),
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
                     f"<p>Click <a href=\"#\" data-wizard-open>Free Instant Quote</a> to tell us about your event. We'll match you with available {nl} providers for your date.</p>"),
                ]

            faq_html, faq_ld = faq_block(faqs)

            other_pages = [fp for fp in all_find_pages if fp["url"] != page_url]
            other_find_html = ""
            if other_pages:
                other_find_links = "\n          ".join(
                    f'<li><a href="{fp["url"]}">{esc(fp["title"])}</a></li>' for fp in other_pages)
                other_find_html = f'''
      <h2>More Rental Pages</h2>
      <ul class="bullet-services">
          {other_find_links}
      </ul>'''

            # Sibling services in this same city — the tightest internal link
            # cluster on the page, so /cities/{city}/{service}/ pages all
            # reinforce each other and the city hub above them.
            sibling_links = "\n          ".join(
                f'<li><a href="{city_service_href(up, loc["slug"])}">{esc(nm2)} in {esc(nl)}</a> '
                f'<span class="muted">({n2} provider{"s" if n2 != 1 else ""})</span></li>'
                for up, nm2, n2 in CITY_SERVICE_INDEX.get(loc["slug"], []) if up != fam["url_prefix"])
            sibling_html = f'''
      <h2>Other Rental Services in {esc(nl)}</h2>
      <ul class="bullet-services">
          {sibling_links}
      </ul>''' if sibling_links else ""

            svc_ld = {"@context": "https://schema.org", "@type": "Service", "serviceType": svc_name,
                      "areaServed": {"@type": "Place", "name": f"{nl}, Georgia"},
                      "provider": {"@type": "LocalBusiness", "name": "Atlanta Bounce House Rental Directory",
                                   "telephone": PHONE_HREF, "areaServed": f"{nl}, GA"},
                      "url": f"{DOMAIN}{page_url}"}
            bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
                {"@type": "ListItem", "position": 2, "name": "Cities", "item": DOMAIN + "/cities/"},
                {"@type": "ListItem", "position": 3, "name": nl, "item": f'{DOMAIN}/cities/{loc["slug"]}/'},
                {"@type": "ListItem", "position": 4, "name": svc_name, "item": f"{DOMAIN}{page_url}"}]}
            extra = (f'<script type="application/ld+json">\n{json.dumps(svc_ld, ensure_ascii=False)}\n</script>\n'
                     f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}\n{LEAFLET_HEAD}')

            clat, clng = location_center(loc, providers)

            page = head(title, desc, f"{DOMAIN}{page_url}", extra)
            page += header("cities") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/cities/">Cities</a> &rsaquo; <a href="/cities/{loc["slug"]}/">{esc(nl)}</a> &rsaquo; {esc(svc_name)}</div>
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
      <p><a href="/cities/{loc["slug"]}/">&larr; All {esc(nl)} providers</a> &middot; <a href="/services/">All rental services</a></p>
      {sibling_html}
      {other_find_html}
    </div>
  </div>
</section>
{faq_html}

<section class="cta-band">
  <div class="container">
    <h2>Book {svc_name} in {esc(nl)} Today</h2>
    <p>Tell us about your event and we'll match you with available {esc(nl)} providers. Free quotes, no obligation.</p>
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
            pd = os.path.join(ROOT, "cities", loc["slug"], fam["url_prefix"])
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
                f'<li><a href="{city_service_href(fam["url_prefix"], loc["slug"])}">{fam["name"]} in {esc(loc["name"])}, GA</a></li>'
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
             f"<p>Click <a href=\"#\" data-wizard-open>Free Instant Quote</a> to tell us about your event and we'll match you with an available provider near you.</p>"),
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

{LEAFLET_JS}
<script src="/js/map-data.js"></script>
<script src="/js/searchmap.js"></script>
<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
        "Find cheap bounce house rentals near you in Atlanta, including $99 specials. Compare budget-friendly, well-reviewed local providers and get a free quote. Call 404-737-1843.",
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
    <a class="btn" href="#" data-wizard-open>Free Instant Quote &rsaquo;</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
        "Live Atlanta Bounce House Rental Leads | Contractor Leaderboard",
        "Live leaderboard of incoming bounce house and party rental leads across Atlanta, Georgia, captured from our website quote form. Subscribe to unlock full contact details.",
        DOMAIN + "/leads/", extra)
    html_out += header("leads") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Leads</div>
    <h1>Live Atlanta Rental Leads</h1>
    <p>Real-time inquiries from customers across Atlanta, captured through our website Free Instant Quote form. Every lead's name is public — subscribe to unlock full contact details and claim the job.</p>
  </div>
</div>

<section>
  <div class="container">
    {featured_image_html(alt_override="Atlanta party rentals set up for a celebration")}
    <div class="login-banner" id="login-banner">
      <div>
        <h3>You're viewing the public leaderboard</h3>
        <p>Names are shown to everyone. Phone, email and event details are reserved for subscribed contractors and the site admin.</p>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <a class="btn" href="https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i" target="_blank" rel="noopener">Subscribe for Full Access</a>
        <button class="btn btn-ghost" data-open-login>Log In</button>
      </div>
    </div>

    <div class="login-banner" id="subscribe-banner" style="display:none;">
      <div>
        <h3>Your account isn't subscribed yet</h3>
        <p>You're logged in, but this account doesn't have an active subscription. Complete checkout with the same email to unlock full lead details.</p>
      </div>
      <a class="btn" href="https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i" target="_blank" rel="noopener">Subscribe Now</a>
    </div>

    <div class="leads-bar" id="logged-bar" style="display:none;">
      <span class="badge-live"><span class="dot"></span> Live feed &mdash; full access</span>
      <button class="btn btn-ghost" id="logout-btn">Log Out</button>
    </div>

    <div id="leads-board"></div>

    <div class="callout" style="margin-top:30px;">
      <p><strong>Want these leads?</strong> <a href="https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i" target="_blank" rel="noopener">Subscribe as a contractor</a> to unlock full contact details on every lead, or <a href="/legal/contact.html">contact us</a> with questions.</p>
      <p style="margin:10px 0 0;"><a href="/dashboard/">View Site Analytics &rsaquo;</a> &mdash; see how much traffic and lead activity the directory is driving in real time.</p>
    </div>
  </div>
</section>

<div class="modal-overlay" id="login-modal" role="dialog" aria-modal="true" aria-labelledby="login-title">
  <div class="modal">
    <button class="modal-close" data-close-login aria-label="Close">&times;</button>
    <h3 id="login-title">Contractor Account</h3>
    <p class="sub">Log in if you already have an account, or sign up and subscribe to unlock full lead details.</p>
    <div id="login-error" class="form-success" style="display:none;background:#fdeaea;border-color:#f3c2c2;color:#a12626;"></div>
    <form id="login-form" novalidate>
      <div class="field"><label for="l-email">Email</label><input id="l-email" name="email" type="email" autocomplete="email" required></div>
      <div class="field"><label for="l-pass">Password</label><input id="l-pass" name="password" type="password" autocomplete="current-password" required></div>
      <button class="btn btn-block" type="submit">Log In</button>
    </form>
    <hr style="margin:22px 0;border:0;border-top:1px solid var(--line);">
    <h3 style="font-size:1.05rem;">New contractor? Create an account</h3>
    <div id="signup-message" class="form-success" style="display:none;"></div>
    <form id="signup-form" novalidate>
      <div class="field"><label for="s-email">Email</label><input id="s-email" name="email" type="email" autocomplete="email" required></div>
      <div class="field"><label for="s-pass">Password</label><input id="s-pass" name="password" type="password" autocomplete="new-password" minlength="6" required></div>
      <button class="btn btn-block btn-ghost" type="submit">Create Account</button>
      <p class="form-note">After signing up, <a href="https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i" target="_blank" rel="noopener">subscribe here</a> with the same email to unlock full lead details.</p>
    </form>
  </div>
</div>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/leads.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "leads")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(html_out)


# ----------------------------------------------------------------- dashboard
def build_dashboard():
    """Public, no-login real-time analytics dashboard at /dashboard.
    Data comes straight from Supabase (public.ATLbounchouserentals_dashboard + the
    existing public.leads_board view) via js/dashboard.js — this is a
    static site with no server, so there's no build-time data here."""
    extra = ""
    html_out = head(
        "Live Site Analytics | Atlanta Bounce House Rentals",
        "Real-time traffic and lead-activity dashboard for the Atlanta Bounce House Rentals directory — sessions, visitors, searches, lead actions and a live event feed.",
        DOMAIN + "/dashboard/", extra)
    html_out += header("dashboard") + f'''
<div class="page-head">
  <div class="container">
    <div class="breadcrumbs"><a href="/">Home</a> &rsaquo; Site Analytics</div>
    <h1>Live Site Analytics</h1>
    <p>Real-time traffic and lead activity across the directory &mdash; updated live as visitors browse. No login required; nothing here is personally identifiable.</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="dash-panel calls-panel">
      <div class="calls-panel-head">
        <h2>Lead Calls We Received</h2>
        <a class="btn" href="https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i" target="_blank" rel="noopener">Subscribe To Receive All Leads</a>
      </div>
      <div id="calls-stats" class="dash-stats"></div>
      <div id="calls-line-chart" class="dash-line-chart"></div>
      <div id="calls-list" class="calls-list"></div>
    </div>

    <div class="dash-range-bar" style="margin-top:30px;">
      <div class="dash-range-toggle" role="group" aria-label="Date range">
        <button type="button" class="dash-range-btn" data-dash-range="7">7 days</button>
        <button type="button" class="dash-range-btn active" data-dash-range="30">30 days</button>
        <button type="button" class="dash-range-btn" data-dash-range="90">90 days</button>
      </div>
    </div>

    <div class="dash-stats" id="dash-stats"></div>

    <div class="dash-grid">
      <div class="dash-panel">
        <h2>Action Breakdown</h2>
        <div id="dash-bar-chart" class="dash-bar-chart"></div>
      </div>
      <div class="dash-panel">
        <h2>Daily Activity Trend</h2>
        <div id="dash-line-chart" class="dash-line-chart"></div>
      </div>
    </div>

    <div class="dash-panel" style="margin-top:22px;">
      <div class="dash-live-head">
        <h2>Live Activity</h2>
        <span class="dash-live-status-wrap"><span class="dot"></span> <span id="dash-live-status">Connecting&hellip;</span></span>
      </div>
      <div class="muted" id="dash-live-count" style="margin-bottom:10px;">0 events since you opened this page</div>
      <div id="dash-live-feed" class="dash-live-feed">
        <div class="muted" data-live-empty>Waiting for activity&hellip;</div>
      </div>
    </div>

    <div class="dash-panel" style="margin-top:22px;">
      <h2>Per-Business Breakdown</h2>
      <div id="dash-business-table" class="dash-table-wrap"></div>
    </div>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
<script src="/js/dashboard.js"></script>
<script src="/js/calls.js"></script>
<script src="/js/wizard.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "dashboard")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(html_out)


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
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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
<script src="/js/analytics.js"></script>
<script src="/js/search-index.js"></script>
<script src="/js/search.js"></script>
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

> Atlanta Bounce House Rentals (atlbouncehouserentals.com) is an independent directory that connects customers in Atlanta, Georgia with {len(providers)} local bounce house and party rental providers. Visitors compare providers by rating, reviews and verification, see typical price ranges, and request free quotes. Booking and quotes: call 404-737-1843.

Key facts:
- Location served: Atlanta, Georgia and surrounding metro (Midtown, Buckhead, Decatur, Sandy Springs, College Park, East Point, Dunwoody, Chamblee and more).
- Phone for quotes and booking: 404-737-1843
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


def build_vercel_redirects(families):
    """Regenerates vercel.json's redirect list: legacy /locations/{city}/ URLs
    (unmigrated cities keep their real page; migrated cities now point at
    /cities/{city}/), plus a permanent redirect from every old
    /find/{service}-{city}-ga/ URL to its new /cities/{city}/{service}/ home
    now that city+service pages live there instead."""
    redirects = [{"source": "/leads.html", "destination": "/leads/", "permanent": True}]

    for loc in LOCATIONS:
        slug = loc["slug"]
        dest = location_href(loc)  # /cities/{slug}/ if migrated, else /locations/{slug}/
        if dest == f"/locations/{slug}/":
            continue  # nothing to redirect — this is still the real page
        redirects.append({"source": f"/locations/{slug}", "destination": dest, "permanent": True})
        redirects.append({"source": f"/locations/{slug}/", "destination": dest, "permanent": True})

    for fam in families:
        if fam["url_prefix"] == CITY_HUB_FAMILY_PREFIX:
            # This family's old per-city URL is what used to live at
            # /find/bounce-house-rentals-{city}-ga/ — now folded into the
            # city hub page itself.
            for loc, matched, url_slug in fam["entries"]:
                old = f"/find/{url_slug}"
                new = city_service_href(fam["url_prefix"], loc["slug"])
                redirects.append({"source": old, "destination": new, "permanent": True})
                redirects.append({"source": old + "/", "destination": new, "permanent": True})
            continue
        for loc, matched, url_slug in fam["entries"]:
            old = f"/find/{url_slug}"
            new = city_service_href(fam["url_prefix"], loc["slug"])
            redirects.append({"source": old, "destination": new, "permanent": True})
            redirects.append({"source": old + "/", "destination": new, "permanent": True})

    cfg = {"redirects": redirects}
    with open(os.path.join(ROOT, "vercel.json"), "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def build_sitemap(providers, find_urls=None, city_urls=None):
    bh_items = json.load(open(os.path.join(ROOT, "data", "bounce-houses.json")))
    urls = ["/", "/services/", "/bounce-houses/", "/locations/",
            "/cheap-bounce-house-rentals/", "/partners.html", "/leads/", "/dashboard/"]
    urls += [f"/services/{s}/" for s in SERVICES]
    urls += [f"/services/{slug}/" for slug, _ in SPECIALTY_SLUGS]
    urls += [product_href(p) for p in PRODUCTS]
    urls += [f"/bounce-houses/{it['slug']}/" for it in bh_items]
    urls += [f"/locations/{l['slug']}/" for l in LOCATIONS if l["slug"] not in MIGRATED_LOCATION_SLUGS]
    urls += find_urls or []
    urls += city_urls or []
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


def build_search_index():
    """Header search bar's data source (js/search.js). Scans every generated
    page's <title> after everything else has been built, so the index can
    never drift from what's actually live on the site — no separate list of
    URLs to keep in sync by hand."""
    skip_dirs = {".git", ".claude", "images", "css", "js", "data", "supabase", "scripts", "api", ".vercel"}
    entries = []

    def add_page(path, url):
        content = open(path, encoding="utf-8").read()
        m = re.search(r"<title>(.*?)</title>", content, re.S)
        title = html.unescape(m.group(1).strip()) if m else url
        entries.append({"t": title, "u": url})

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
        rel = os.path.relpath(dirpath, ROOT)
        if "index.html" in filenames:
            url = "/" if rel == "." else "/" + rel.replace(os.sep, "/") + "/"
            add_page(os.path.join(dirpath, "index.html"), url)
        # Flat .html files (legal/about.html, partners.html, ...) — 404.html
        # is intentionally excluded, it's not a real navigable page.
        for fn in filenames:
            if fn.endswith(".html") and fn not in ("index.html", "404.html"):
                url_path = fn if rel == "." else f"{rel}/{fn}"
                add_page(os.path.join(dirpath, fn), "/" + url_path.replace(os.sep, "/"))

    entries.sort(key=lambda e: e["u"])
    js = "window.ABHR_SEARCH_INDEX = " + json.dumps(entries, ensure_ascii=False) + ";\n"
    open(os.path.join(ROOT, "js", "search-index.js"), "w").write(js)
    return len(entries)


def main():
    providers = json.load(open(os.path.join(ROOT, "data", "providers.json")))
    for it in providers:
        it["services"] = map_services(it)
    providers.sort(key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0), x["name"].lower()))

    MIGRATED_LOCATION_SLUGS.clear()
    MIGRATED_LOCATION_SLUGS.update(
        loc["slug"] for loc in LOCATIONS if providers_for_location(loc, providers))

    families = compute_find_families(providers)
    CITY_SERVICE_INDEX.clear()
    CITY_SERVICE_INDEX.update(city_service_index(families))

    build_map_data(providers)
    build_index(providers, families)
    build_partners(providers)
    build_partner_pages(providers)
    build_services_index(providers, families)
    build_service_pages(providers)
    build_specialty_service_pages()
    build_product_pages()
    build_bounce_houses()
    build_locations(providers)
    city_urls = build_cities(providers)
    find_urls = build_find_pages(providers, families)
    build_cheap(providers)
    build_leads()
    build_dashboard()
    build_legal()
    build_404()
    build_vercel_redirects(families)
    build_sitemap(providers, find_urls, city_urls)
    build_llms(providers)
    n_indexed = build_search_index()
    print(f"Built site: {len(providers)} providers + services + bounce houses + legal + leads + dashboard + llms.txt + search index ({n_indexed} pages)")


if __name__ == "__main__":
    main()
