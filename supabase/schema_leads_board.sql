-- Atlanta Bounce House Rentals — /leads.html leaderboard access control
-- Supabase project: ATLBounceHouseRentals_Leads_Board
-- Run this once in the Supabase SQL editor (https://supabase.com/dashboard/project/tbqigevoksabizjogvtm/sql/new)
-- Requires supabase/schema.sql (the leads table) to already exist.

-- ─── 1. Subscribers table ───────────────────────────────────────────────
-- Contractors who paid via the Stripe subscription link
-- (https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i) get full lead access
-- once their row here has active = true. There is no Stripe webhook wired
-- up yet, so after someone subscribes:
--   1. They sign up for an account on /leads.html with the SAME email
--      they used to check out on Stripe.
--   2. You add/activate their email below (Table Editor > subscribers,
--      or the SQL at the bottom of this file) once you see the Stripe
--      payment come through.
create table if not exists public.subscribers (
  email          text primary key,
  active         boolean not null default true,
  subscribed_at  timestamptz not null default now(),
  notes          text
);

alter table public.subscribers enable row level security;

-- A logged-in user can check only their OWN row (needed so the leads page
-- can tell whether the current visitor is unlocked) — nothing else.
drop policy if exists "Users can check their own subscription" on public.subscribers;
create policy "Users can check their own subscription"
  on public.subscribers
  for select
  to authenticated
  using (email = auth.jwt() ->> 'email');

-- ─── 2. Full-access read policies on the real leads table ──────────────
-- Everyone else (including anonymous visitors) gets NO direct access to
-- public.leads — only the safe view below. These two policies are the
-- only way to read phone/email/message off the real table.

-- You, the site owner, always see every column of every lead.
drop policy if exists "Admin can read all leads" on public.leads;
create policy "Admin can read all leads"
  on public.leads
  for select
  to authenticated
  using (auth.jwt() ->> 'email' = 'mindfulmarketingad@gmail.com');

-- Active subscribers see every column of every lead too.
drop policy if exists "Active subscribers can read all leads" on public.leads;
create policy "Active subscribers can read all leads"
  on public.leads
  for select
  to authenticated
  using (exists (
    select 1 from public.subscribers s
    where s.email = auth.jwt() ->> 'email' and s.active = true
  ));

grant select on public.leads to authenticated;

-- ─── 3. Public leaderboard view — name only, nothing sensitive ─────────
-- Created here (as the SQL editor's role, which owns/bypasses RLS on the
-- base table) so it is safe to grant to anon/authenticated: this view
-- physically contains only id/name/created_at — phone, email, message,
-- ZIP etc. never leave the database for a non-entitled visitor, so there
-- is nothing for view-source/devtools to expose.
--
-- Only real leads submitted from the live site are shown — filters out
-- anything captured from a dev/staging/localhost copy of the wizard.
-- Matched on the domain substring (not an exact www/non-www prefix) so
-- it's not sensitive to which host variant Vercel actually serves.
create or replace view public.leads_board as
select id, name, created_at
from public.leads
where page_url ilike '%atlbouncehouserentals.com%'
order by created_at desc;

grant select on public.leads_board to anon, authenticated;

-- ─── To activate a contractor after they pay via Stripe ────────────────
-- insert into public.subscribers (email) values ('contractor@example.com')
--   on conflict (email) do update set active = true;
