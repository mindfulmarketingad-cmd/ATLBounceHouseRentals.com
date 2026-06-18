#!/usr/bin/env python3
"""Static-site generator for Atlanta Bounce House Rentals.
Reads data/providers.json and regenerates the whole site:
homepage, services, individual service pages, partners directory,
individual partner pages, leads board, legal pages, 404, sitemap.

Theme: light blue + black. No emojis. No ad placeholders.
Business phone/contact are never published — the site phone is shown instead.
Run: python3 build.py
"""
import json, os, re, html

ROOT = os.path.dirname(os.path.abspath(__file__))
PHONE_DISPLAY = "(401) 889-0182"
PHONE_HREF = "+14018890182"
DOMAIN = "https://atlbouncehouserentals.com"

SERVICES = {
    "classic-bounce-house-rentals": "Classic Bounce House Rentals",
    "bounce-and-slide-combo-rentals": "Bounce and Slide Combo Rentals",
    "water-slide-rentals": "Water Slide Rentals",
    "obstacle-course-rentals": "Obstacle Course Rentals",
    "concession-rentals": "Concession Rentals",
    "tents-tables-and-chair-rentals": "Tents, Tables and Chair Rentals",
    "interactive-rentals": "Interactive Rentals",
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
    "party-package-rentals": "Party Packages",
    "party-entertainment-and-staff-rentals": "Entertainment & Staff",
}

KEYWORDS = [
    (["water slide", "waterslide", "water-slide", "splash", "slip"], "water-slide-rentals"),
    (["combo", "bounce and slide", "bounce & slide", "slide combo"], "bounce-and-slide-combo-rentals"),
    (["obstacle", "course"], "obstacle-course-rentals"),
    (["concession", "popcorn", "cotton candy", "snow cone", "snowcone", "shaved ice", "frozen drink"], "concession-rentals"),
    (["tent", "table", "chair", "canopy", "linen", "drapery"], "tents-tables-and-chair-rentals"),
    (["photo booth", "photobooth", "arcade", "amusement", "game", "interactive", "dunk", "carnival", "mechanical", "axe", "laser"], "interactive-rentals"),
    (["dj", "bartend", "bartending", "entertainer", "entertainment", "host", "character", "costume", "clown", "face paint", "balloon", "limousine", "limo", "staff", "magician", "videograph", "catering", "caterer", "petting", "pony"], "party-entertainment-and-staff-rentals"),
    (["bounce", "jump", "jumper", "moonwalk", "moon walk", "inflatable", "bouncer", "bouncy", "castle"], "classic-bounce-house-rentals"),
    (["package", "party rental", "party equipment", "event rental", "event planner", "event management", "party planner", "party supply"], "party-package-rentals"),
]

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
        <a href="/services/"{cls("services")}>Services</a>
        <a href="/bounce-houses/"{cls("bounce-houses")}>Bounce Houses</a>
        <a href="/locations/"{cls("locations")}>Service Areas</a>
        <a href="/partners.html"{cls("partners")}>Partners</a>
        <a href="/leads.html"{cls("leads")}>Leads</a>
      </nav>
      <a class="phone-cta" href="tel:{PHONE_HREF}"><span><span class="ph-label">Call Now</span>{PHONE_DISPLAY}</span></a>
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

ADSENSE = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script>'


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
<meta property="og:image" content="{DOMAIN}/images/hero-bounce-house.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{DOMAIN}/images/hero-bounce-house.svg">
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
          <td class="arrow"><a href="/partners/{it["slug"]}/" aria-label="View {esc(it["name"])}">&#8599;</a></td>
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
        f'<li><a href="/locations/{l["slug"]}/">Bounce House Rentals in {esc(l["name"])}</a></li>'
        for l in LOCATIONS)
    chips = "\n          ".join(
        f'<button type="button" data-q="{SERVICES[s].lower()}">{SERVICES[s]}</button>' for s in SERVICES)

    faqs = [
        ("How much does it cost to rent a bounce house in Atlanta?",
         "<p>In Atlanta, a classic bounce house typically rents for about $120&ndash;$260 per day, while larger combo units, water slides and obstacle courses range from roughly $180 to $900+ depending on size. Full party packages run from around $220 to $1,800+. Final pricing depends on the date, delivery distance, rental length and add-ons. <a href=\"/#providers\">Request a free quote</a> for an exact figure.</p>"),
        ("How do I book a bounce house rental in Atlanta?",
         "<p>Use the free quote form on this page or call <a href=\"tel:+14018890182\">(401) 889-0182</a>. Tell us your event date, ZIP code and what you need, and we'll match you with available providers from our Atlanta directory so you can compare and book.</p>"),
        ("What areas around Atlanta do you serve?",
         "<p>Our directory providers serve the City of Atlanta and the surrounding metro, including Midtown, Buckhead, Downtown, Decatur, Sandy Springs, College Park, East Point, Dunwoody, Chamblee and more.</p>"),
        ("What types of bounce houses and party rentals are available?",
         "<p>You can rent classic bounce houses, bounce-and-slide combos, water slides, obstacle courses, concession machines, tents, tables and chairs, interactive games, complete party packages and event staff. See the <a href=\"/services/\">full list of services</a>.</p>"),
        ("Are the rental providers verified?",
         "<p>Yes. Each provider listing shows whether the business is verified on Google along with its star rating and review count, so you can choose a trusted, well-reviewed Atlanta company with confidence.</p>"),
        ("How far in advance should I book a bounce house in Atlanta?",
         "<p>For weekends in spring and summer&mdash;Atlanta's busiest party season&mdash;book 2 to 4 weeks ahead. Water slides and large combos sell out fastest. For last-minute needs, call <a href=\"tel:+14018890182\">(401) 889-0182</a> and we'll check live availability.</p>"),
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
      <h1>Atlanta Bounce House Rental Directory</h1>
      <p class="lead">Find, compare and book bounce houses, water slides and party rentals from trusted providers across Atlanta, Georgia.</p>
      <div class="wizard-cta-block">
        <p class="wizard-hero-tagline">Tell us about your event and we'll match you with the right Atlanta providers.</p>
        <a class="btn" href="#" id="wizard-open" style="font-size:1.1rem;padding:16px 32px;">Book Now &rsaquo;</a>
        <div class="hero-trust">
          <span>Free quotes</span>
          <span>No obligation</span>
          <span>98 Atlanta providers</span>
          <span>Fast response</span>
        </div>
      </div>
      <ul class="hero-points">
        <li>Compare every local provider in one place</li>
        <li>Free, no-obligation quotes in minutes</li>
        <li>Serving Atlanta and all surrounding metro areas</li>
      </ul>
    </div>

    <div class="quote-card">
      <h2>Get a Free Quote</h2>
      <p class="sub">Tell us about your event and we'll connect you with available Atlanta providers.</p>
      <form data-quote-form novalidate>
        <div data-success class="form-success" style="display:none;">
          Thanks! Your request was received. An Atlanta provider will contact you shortly. Need it now? Call <strong>{PHONE_DISPLAY}</strong>.
        </div>
        <div data-fields>
          <div class="field"><label for="q-name">Full Name</label><input id="q-name" name="name" type="text" required></div>
          <div class="field"><label for="q-phone">Phone</label><input id="q-phone" name="phone" type="tel" required></div>
          <div class="field"><label for="q-email">Email</label><input id="q-email" name="email" type="email" required></div>
          <div class="field"><label for="q-service">Service Needed</label>
            <select id="q-service" name="service">
              {"".join(f'<option value="{SERVICES[s]}">{SERVICES[s]}</option>' for s in SERVICES)}
            </select>
          </div>
          <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div><label for="q-date">Event Date</label><input id="q-date" name="event_date" type="date"></div>
            <div><label for="q-zip">ZIP Code</label><input id="q-zip" name="zip" type="text" placeholder="30303"></div>
          </div>
          <div class="field"><label for="q-msg">Event Details</label><textarea id="q-msg" name="message" rows="2" placeholder="Guests, ages, venue..."></textarea></div>
          <button class="btn btn-block" type="submit">Get My Free Quote</button>
          <p class="form-note">No spam. Your details are only shared with matched providers.</p>
        </div>
      </form>
    </div>
  </div>
</section>

<section id="services">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">What You Can Rent</div>
      <h2>All Bounce House Rental Services In Atlanta Georgia</h2>
      <p>Explore every rental category available across the Atlanta metro and request a free quote on any of them.</p>
    </div>
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
    <ul class="bullet-services" style="columns:3;margin-bottom:24px;">
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
    <p>Get matched with available providers in minutes. Compare quotes, check availability and lock in your date with confidence.</p>
    <a class="btn" href="tel:{PHONE_HREF}">Call {PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

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
    <p>Browse {len(providers)} bounce house and party rental businesses serving Atlanta and the surrounding Georgia metro. Compare ratings and reviews below, then call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> for a free quote and we'll match you with the right provider.</p>
  </div>
</div>

<section>
  <div class="container">
{provider_table(providers)}
    <div class="callout" style="margin-top:26px;">
      <p><strong>Ready to book?</strong> Contact for every provider is handled through the directory &mdash; call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> or <a href="/#providers">request a free quote</a> and we'll connect you with an available company for your event.</p>
    </div>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/directory.js"></script>
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
  </div>
</div>

<section>
  <div class="container">
    <div class="grid" style="grid-template-columns:1.6fr 1fr; gap:40px; align-items:start;">
      <div class="content">
        <h2>About {esc(name)}</h2>
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
          <h2>Request a Free Quote</h2>
          <p class="sub">Check availability with {esc(name)} and compare Atlanta providers.</p>
          <a class="btn btn-block" href="tel:{PHONE_HREF}">Call {PHONE_DISPLAY}</a>
          <p class="form-note" style="margin-top:14px;">Or <a href="/#providers">submit a quote request</a> and we'll match you with available providers.</p>
        </div>

        <div class="info-box">
          <h3>Business Hours</h3>
          <table class="hours">
        {hours_rows(it)}
          </table>
          <p class="muted" style="font-size:0.8rem;margin:12px 0 0;">Hours from Google. Call to confirm holiday availability.</p>
        </div>
      </aside>
    </div>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
<script src="/js/partners.js"></script>
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


def build_services_index():
    links = "\n      ".join(
        f'<li><a href="/services/{s}/">{SERVICES[s]} in Atlanta Georgia</a></li>' for s in SERVICES)
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
    <ul class="bullet-services">
      {links}
    </ul>
    <div class="callout">
      <p><strong>Not sure what you need?</strong> Call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a> or <a href="/#providers">request a free quote</a> and an Atlanta provider will help you choose the right rentals for your event.</p>
    </div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2>Get a Free Atlanta Bounce House Quote</h2>
    <p>Compare providers and pricing across the Atlanta metro in minutes.</p>
    <a class="btn" href="/#providers">Request a Free Quote</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
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
            f'<li><a href="/locations/{l["slug"]}/">{SERVICES[slug]} in {esc(l["name"])}</a></li>'
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
             f"<p>Call <a href=\"tel:{PHONE_HREF}\">{PHONE_DISPLAY}</a> or submit the quote form on this page. We'll match you with available Atlanta providers that offer {nml} for your date.</p>"),
            (f"Do providers deliver {nml} across metro Atlanta?",
             f"<p>Yes. Directory providers deliver {nml} to Atlanta and surrounding areas including Midtown, Buckhead, Decatur, Sandy Springs, College Park and East Point, and they handle setup and pickup.</p>"),
            (f"How far in advance should I reserve {nml}?",
             f"<p>Booking 2&ndash;4 weeks ahead is recommended for weekend dates in Atlanta's busy spring and summer season. Last-minute requests are welcome too&mdash;call {PHONE_DISPLAY} to check availability.</p>"),
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
        img_html = (f'<img class="bh-card-img" src="{it["images"][0]}" alt="{esc(it["name"])}" loading="lazy" width="600" height="450">'
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
    <h2>Need Help Choosing?</h2>
    <p>Call us and we'll match you with the right bounce house for your event size and budget.</p>
    <a class="btn" href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
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
            f'<img src="{esc(src)}" alt="{esc(it["name"])}" loading="lazy">' for src in imgs
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
          <p class="sub">Call us or fill out the form below and we&rsquo;ll confirm availability and send you a quote.</p>
          <a class="bh-call-btn" href="tel:{PHONE_HREF}">
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h2.28a1 1 0 01.95.68l1.1 3.3a1 1 0 01-.23 1.03L7.83 9.24a16.06 16.06 0 006.93 6.93l1.23-1.27a1 1 0 011.03-.23l3.3 1.1a1 1 0 01.68.95V19a2 2 0 01-2 2h-1C9.16 21 3 14.84 3 7V5z"/></svg>
            {PHONE_DISPLAY}
          </a>
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
    <p>Call us now to check availability and lock in your date with a $50 deposit.</p>
    <a class="btn" href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
</body>
</html>
'''
        slug_dir = os.path.join(ROOT, "bounce-houses", it["slug"])
        os.makedirs(slug_dir, exist_ok=True)
        open(os.path.join(slug_dir, "index.html"), "w").write(page)


# ----------------------------------------------------------------- locations
def build_locations(providers):
    """Service-area landing pages: /locations/ index + one page per metro city/district.
    Every page links up to the index, across to nearby areas, down to services and
    matched providers, and out to the cheap-rentals page — so none are orphaned."""

    # --- index page ---
    cards = []
    for loc in LOCATIONS:
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

    item_ld = {"@context": "https://schema.org", "@type": "ItemList",
               "itemListElement": [
                   {"@type": "ListItem", "position": i + 1,
                    "name": f'Bounce House Rentals in {l["name"]}',
                    "url": f'{DOMAIN}/locations/{l["slug"]}/'}
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
    <p>We connect you with bounce house and party rental providers in every corner of the Atlanta metro. Choose your city or neighborhood below to see local providers, pricing and a free quote, or call <a href="tel:{PHONE_HREF}">{PHONE_DISPLAY}</a>.</p>
  </div>
</div>

<section>
  <div class="container">
    <div class="loc-grid">
{cards_html}
    </div>
  </div>
</section>

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
    <p>Compare local Atlanta providers and lock in your date. Free quotes, no obligation.</p>
    <a class="btn" href="tel:{PHONE_HREF}">Call {PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
</body>
</html>
'''
    d = os.path.join(ROOT, "locations")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(idx)

    # --- individual city pages ---
    for loc in LOCATIONS:
        name = loc["name"]
        nl = name
        matched = providers_for_location(loc, providers)
        if matched:
            prov_links = "\n          ".join(
                f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>'
                f'{" &mdash; " + str(p["reviews"]) + " reviews" if p.get("reviews") else ""}</li>'
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
            f'<li><a href="/locations/{x["slug"]}/">Bounce House Rentals in {esc(x["name"])}</a></li>' for x in nearby)

        faqs = [
            (f"How much does it cost to rent a bounce house in {nl}?",
             f"<p>In {nl}, a classic bounce house typically rents for about $120&ndash;$260 per day, with combo slides, water slides and obstacle courses running roughly $180&ndash;$900+ depending on size. Final pricing depends on your date, delivery distance and rental length. <a href=\"/cheap-bounce-house-rentals/\">See current $99 specials</a> or <a href=\"/#providers\">request a free quote</a>.</p>"),
            (f"Do providers deliver bounce houses to {nl}?",
             f"<p>Yes. Directory providers deliver bounce houses, water slides, tents, tables, chairs and concessions throughout {nl}, including {esc(hoods)}, and handle setup and pickup.</p>"),
            (f"How far in advance should I book a bounce house in {nl}?",
             f"<p>For weekend dates in {nl} during Atlanta's busy spring and summer season, book 2&ndash;4 weeks ahead. Last-minute requests are welcome too&mdash;call {PHONE_DISPLAY} to check availability.</p>"),
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
                 f'<script type="application/ld+json">\n{json.dumps(bc, ensure_ascii=False)}\n</script>\n{faq_ld}')

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

<section>
  <div class="container">
    <div class="grid" style="grid-template-columns:1.6fr 1fr; gap:48px; align-items:start;">
      <div class="content">
        <h2>Bounce House &amp; Party Rentals Serving {esc(nl)}</h2>
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
          <h2>Free Quote</h2>
          <p class="sub">Request pricing for bounce house rentals in {esc(nl)}.</p>
          <form data-quote-form novalidate>
            <div data-success class="form-success" style="display:none;">
              Thanks! A provider serving {esc(nl)} will contact you shortly. Call <strong>{PHONE_DISPLAY}</strong> for immediate help.
            </div>
            <div data-fields>
              <div class="field"><label for="q-name">Full Name</label><input id="q-name" name="name" type="text" required></div>
              <div class="field"><label for="q-phone">Phone</label><input id="q-phone" name="phone" type="tel" required></div>
              <div class="field"><label for="q-email">Email</label><input id="q-email" name="email" type="email" required></div>
              <input type="hidden" name="area" value="{esc(nl)}">
              <div class="field"><label for="q-service">Service</label>
                <select id="q-service" name="service">
              {"".join(f'<option value="{SERVICES[x]}">{SERVICES[x]}</option>' for x in SERVICES)}
                </select>
              </div>
              <div class="field"><label for="q-date">Event Date</label><input id="q-date" name="event_date" type="date"></div>
              <div class="field"><label for="q-zip">ZIP Code</label><input id="q-zip" name="zip" type="text" placeholder="{esc(loc["zips"][0])}"></div>
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
    <h2>Book a Bounce House in {esc(nl)} Today</h2>
    <p>Compare available {esc(nl)} providers and lock in your date. Free quotes, no obligation.</p>
    <a class="btn" href="tel:{PHONE_HREF}">Call {PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
</body>
</html>
'''
        sd = os.path.join(ROOT, "locations", loc["slug"])
        os.makedirs(sd, exist_ok=True)
        open(os.path.join(sd, "index.html"), "w").write(page)


# ----------------------------------------------------------------- cheap / $99 landing
def build_cheap(providers):
    """High-intent landing page for 'cheap bounce house rentals near me' and
    '$99 bounce house rental' — both surfaced as ranking opportunities in GSC."""
    top = sorted(providers, key=lambda x: (-(x["rating"] or 0), -(x["reviews"] or 0)))[:8]
    prov_links = "\n          ".join(
        f'<li><a href="/partners/{p["slug"]}/">{esc(p["name"])}</a>'
        f'{" &mdash; " + str(p["rating"]) + "&#9733;" if p.get("rating") else ""}</li>' for p in top)
    loc_links = "\n          ".join(
        f'<li><a href="/locations/{l["slug"]}/">Cheap bounce house rentals in {esc(l["name"])}</a></li>'
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
    <p>Compare budget providers and lock in your date. Free quotes, no obligation.</p>
    <a class="btn" href="tel:{PHONE_HREF}">Call {PHONE_DISPLAY}</a>
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
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
    {p["body"]}
  </div>
</section>

{FOOTER}

<script src="/js/main.js"></script>
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
    <p style="margin-top:24px;"><a class="btn" href="/">Back to Home</a> &nbsp; <a class="btn btn-ghost" href="/services/">Browse Services</a></p>
  </div>
</section>

<script src="/js/main.js"></script>
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


def build_sitemap(providers):
    bh_items = json.load(open(os.path.join(ROOT, "data", "bounce-houses.json")))
    urls = ["/", "/services/", "/bounce-houses/", "/locations/",
            "/cheap-bounce-house-rentals/", "/partners.html", "/leads.html"]
    urls += [f"/services/{s}/" for s in SERVICES]
    urls += [f"/bounce-houses/{it['slug']}/" for it in bh_items]
    urls += [f"/locations/{l['slug']}/" for l in LOCATIONS]
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

    build_index(providers)
    build_partners(providers)
    build_partner_pages(providers)
    build_services_index()
    build_service_pages(providers)
    build_bounce_houses()
    build_locations(providers)
    build_cheap(providers)
    build_leads()
    build_legal()
    build_404()
    build_sitemap(providers)
    build_llms(providers)
    print(f"Built site: {len(providers)} providers + services + bounce houses + legal + leads + llms.txt")


if __name__ == "__main__":
    main()
