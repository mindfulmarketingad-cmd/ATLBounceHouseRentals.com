# Atlanta Bounce House Rentals — Directory Website

A minimalistic, authoritative directory website connecting customers with bounce
house and party rental providers across **Atlanta, Georgia**.

Main keyword: **Atlanta Bounce House Rental**

## Pages

| Page | Path |
| --- | --- |
| Homepage (hero + free quote form, map, services, providers) | `/index.html` |
| Services index (all services, bulleted, linked) | `/services/index.html` |
| Individual service pages (with small/medium/large price estimates) | `/services/<slug>/index.html` |
| Partners directory | `/partners.html` |
| Leads board (login-gated, blurred for guests) | `/leads.html` |
| About / Contact / Privacy / Terms / Disclaimer | `/legal/*.html` |

### Services
- Classic Bounce House Rentals
- Bounce and Slide Combo Rentals
- Water Slide Rentals
- Obstacle Course Rentals
- Concession Rentals
- Tents, Tables and Chair Rentals
- Interactive Rentals
- Party Package Rentals
- Party Entertainment and Staff Rentals

## Tech

Pure static HTML/CSS/JS — no build step, deployable on any static host
(Netlify, Vercel, GitHub Pages, Cloudflare Pages, S3, etc.).

- `css/style.css` — shared design system (minimal, navy/blue, responsive).
- `js/main.js` — mobile nav + quote form handling.
- `js/leads.js` — leads board rendering, partner login gating, blur for guests.

## Leads board

The quote form stores submissions in `localStorage` for the demo so they appear
on the Leads board. Guests see leads with contact details **blurred and locked**.
Partners log in to reveal full details and click-to-call.

**Demo partner login:** `partner@atlbouncehouserentals.com` / `atlanta2026`

> ⚠️ The login + storage is a **front-end demo only**. For production, replace it
> with real server-side authentication and a database so lead contact details are
> never delivered to anonymous browsers. Wire the quote form and your VAPI phone
> line to that backend.

## Google AdSense

Built to AdSense approval standards: original content, clear navigation, mobile
responsive, and full legal pages (Privacy Policy with AdSense/cookie disclosures,
Terms, Disclaimer, About, Contact).

Before requesting approval:
1. Replace every `ca-pub-XXXXXXXXXXXXXXXX` in the HTML with your AdSense publisher ID.
2. Replace `pub-XXXXXXXXXXXXXXXX` in `ads.txt`.
3. Update the domain in `sitemap.xml`, `robots.txt` and canonical tags if different.

## Local preview

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```
