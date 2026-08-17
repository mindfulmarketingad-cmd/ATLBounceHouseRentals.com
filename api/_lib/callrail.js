/* CallRail v3 API client — server-only. Never import this from client-side
   code; it reads process.env.CALLRAIL_API_KEY and that must never reach the
   browser bundle. Called only from api/calls.js (a Vercel serverless
   function), which is the one place allowed to hold the key.
*/

const CALLRAIL_BASE = "https://api.callrail.com/v3";
const FIELDS = [
  "recording", "recording_duration", "transcription", "source_name", "medium",
  "keywords", "landing_page_url", "device_type", "first_call", "total_calls",
  "prior_calls", "tags"
].join(",");

function authHeader() {
  const key = process.env.CALLRAIL_API_KEY;
  if (!key) throw new Error("CALLRAIL_API_KEY is not set");
  return { Authorization: `Token token="${key}"` };
}

async function callrailFetch(path) {
  const res = await fetch(`${CALLRAIL_BASE}${path}`, { headers: authHeader() });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`CallRail ${res.status}: ${body.slice(0, 300)}`);
  }
  return res.json();
}

async function getAccountId() {
  const data = await callrailFetch("/a.json");
  const accounts = data.accounts || data;
  if (!Array.isArray(accounts) || !accounts.length) {
    throw new Error("No CallRail accounts returned for this API key");
  }
  return accounts[0].id;
}

// Fetches inbound calls to `trackingPhoneNumber`, most recent first.
// Paginated up to maxPages (default 5 / up to 500 calls) — plenty for a
// trend chart + recent-call list without hammering the API on every page
// load. `totalRecords` (the account's true lifetime count for this number,
// read straight off page 1) is returned separately so the "Total" stat is
// exact even when we don't paginate through every page.
async function listInboundCalls(trackingPhoneNumber, { maxPages = 5, perPage = 100 } = {}) {
  const accountId = await getAccountId();
  let page = 1;
  let totalPages = 1;
  let totalRecords = 0;
  const calls = [];

  do {
    const qs = new URLSearchParams({
      direction: "inbound",
      tracking_phone_number: trackingPhoneNumber,
      sort: "start_time",
      order: "desc",
      fields: FIELDS,
      per_page: String(perPage),
      page: String(page)
    });
    const data = await callrailFetch(`/a/${accountId}/calls.json?${qs.toString()}`);
    calls.push(...(data.calls || []));
    totalPages = data.total_pages || 1;
    totalRecords = data.total_records != null ? data.total_records : calls.length;
    page++;
  } while (page <= totalPages && page <= maxPages);

  return { calls, totalRecords };
}

module.exports = { authHeader, getAccountId, listInboundCalls };
