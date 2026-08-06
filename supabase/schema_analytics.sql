-- Atlanta Bounce House Rentals — public real-time analytics (/dashboard)
-- Supabase project: ATLBounceHouseRentals_Leads_Board
-- Run this once in the Supabase SQL editor (https://supabase.com/dashboard/project/tbqigevoksabizjogvtm/sql/new)

create extension if not exists pgcrypto;

-- ─── 1. Event table ──────────────────────────────────────────────────────
-- One row per tracked interaction. No PII: just paths, event types and
-- browser-generated session/visitor ids (random strings stored in
-- sessionStorage/localStorage, not tied to any real identity). Because
-- there's nothing sensitive in here, both SELECT and INSERT are public —
-- SELECT so the /dashboard page can query aggregates and subscribe to
-- Realtime changes straight from the browser with the anon key, INSERT so
-- the site's plain client-side tracker (no server, this is a static site)
-- can log events the same way js/wizard.js already logs leads.
create table if not exists public.analytics_events (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  event_type    text not null check (event_type in (
                  'pageview', 'listing_view', 'call_click',
                  'directions_click', 'search', 'review_click'
                )),
  path          text,
  referrer      text,
  session_id    text,
  visitor_id    text,
  listing_slug  text,
  listing_name  text,
  city          text,
  query         text
);

alter table public.analytics_events enable row level security;

drop policy if exists "Public can log analytics events" on public.analytics_events;
create policy "Public can log analytics events"
  on public.analytics_events
  for insert
  to anon, authenticated
  with check (true);

drop policy if exists "Public can read analytics events" on public.analytics_events;
create policy "Public can read analytics events"
  on public.analytics_events
  for select
  to anon, authenticated
  using (true);

grant select, insert on public.analytics_events to anon, authenticated;

-- ─── 2. Indexes ──────────────────────────────────────────────────────────
create index if not exists analytics_events_created_at_idx on public.analytics_events (created_at desc);
create index if not exists analytics_events_event_type_idx on public.analytics_events (event_type);
create index if not exists analytics_events_listing_slug_idx on public.analytics_events (listing_slug);
create index if not exists analytics_events_path_idx on public.analytics_events (path);
create index if not exists analytics_events_session_id_idx on public.analytics_events (session_id);

-- ─── 3. Realtime ─────────────────────────────────────────────────────────
-- Add the table to the supabase_realtime publication so the /dashboard
-- page's live activity panel can subscribe to postgres_changes over
-- Realtime. Guarded so this script is safe to re-run — adding a table
-- that's already in the publication throws an error otherwise.
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'analytics_events'
  ) then
    alter publication supabase_realtime add table public.analytics_events;
  end if;
end $$;
