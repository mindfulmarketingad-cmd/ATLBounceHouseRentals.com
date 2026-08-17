/* Vercel serverless function — GET /api/calls
   Server-only: holds process.env.CALLRAIL_API_KEY and never sends it to the
   browser. Returns a sanitized (phone-masked, tags-flattened) call list for
   the /dashboard page's "Lead Calls We Received" section. This site is
   static HTML with no other backend, so this one endpoint is the sole place
   that talks to CallRail.
*/

const { listInboundCalls } = require("./_lib/callrail");

// Must match PHONE_HREF in build.py — the site's published number IS the
// CallRail tracking number for this site.
const TRACKING_PHONE_NUMBER = "+14047371843";

// Keeps all digits except the last 4, replaced with bullets, e.g.
// "+14048675309" -> "+1404867••••". Applied to every phone number in the
// response so raw numbers never leave the server.
function maskPhone(phone) {
  if (!phone) return "";
  const str = String(phone);
  if (str.length <= 4) return "•".repeat(str.length);
  return str.slice(0, -4) + "••••";
}

function shapeCall(c) {
  return {
    id: c.id,
    start_time: c.start_time,
    duration: c.duration || 0,
    answered: !!c.answered,
    voicemail: !!c.voicemail,
    customer_name: c.customer_name || "",
    customer_phone_masked: maskPhone(c.customer_phone_number),
    business_phone_masked: maskPhone(c.business_phone_number),
    first_call: !!c.first_call,
    total_calls: c.total_calls || 1,
    prior_calls: c.prior_calls || 0,
    source_name: c.source_name || "",
    medium: c.medium || "",
    keywords: c.keywords || "",
    landing_page_url: c.landing_page_url || "",
    device_type: c.device_type || "",
    // CallRail returns tags as an array of {id, name, ...} objects, not
    // strings — flatten to names here so nothing downstream ever tries to
    // render a raw tag object.
    tags: Array.isArray(c.tags) ? c.tags.map((t) => (t && t.name) || "").filter(Boolean) : [],
    recording: c.recording || null,
    transcription: c.transcription || null
  };
}

module.exports = async function handler(req, res) {
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }
  try {
    const { calls, totalRecords } = await listInboundCalls(TRACKING_PHONE_NUMBER);
    res.setHeader("Cache-Control", "public, max-age=30, stale-while-revalidate=60");
    res.status(200).json({
      calls: calls.map(shapeCall),
      totalRecords
    });
  } catch (err) {
    res.status(500).json({ error: "Unable to load calls right now.", detail: String((err && err.message) || err) });
  }
};
