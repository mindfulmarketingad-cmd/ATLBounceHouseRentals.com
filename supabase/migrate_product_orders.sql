-- Atlanta Bounce House Rentals — product request / order fields on public.leads
-- Supabase project: ATLBounceHouseRentals_Leads_Board
-- Run this once in the Supabase SQL editor (https://supabase.com/dashboard/project/tbqigevoksabizjogvtm/sql/new)
--
-- Adds everything needed to invoice and drop-service a product request
-- submitted from a /services/{service}/{product}/ page (e.g. the Gold
-- Chiavari Chair page). The existing wizard columns are untouched — a
-- product request just fills in a different subset of the same table, so
-- /leads/ and the /dashboard "Leads Received" count keep working unchanged.
--
-- Safe to re-run: every ADD COLUMN is IF NOT EXISTS.

-- ─── What they ordered ──────────────────────────────────────────────────
alter table public.leads add column if not exists request_type      text;   -- 'product_request' vs the wizard's null/'wizard'
alter table public.leads add column if not exists product_name      text;   -- "Gold Chiavari Chair with White Pad"
alter table public.leads add column if not exists product_slug      text;   -- "gold-chiavari-chair-white-pad"
alter table public.leads add column if not exists product_variant   text;   -- cushion colour chosen
alter table public.leads add column if not exists quantity          integer;
alter table public.leads add column if not exists unit_price        numeric(10,2);
alter table public.leads add column if not exists delivery_fee      numeric(10,2);  -- flat standard delivery fee (drop-off/pickup only, no setup)
alter table public.leads add column if not exists estimated_total   numeric(10,2);  -- unit_price * quantity + delivery_fee

-- ─── Where it's going (invoice + delivery) ──────────────────────────────
-- zip_code already exists from the wizard schema and is reused here.
alter table public.leads add column if not exists delivery_address  text;
alter table public.leads add column if not exists delivery_city     text;
alter table public.leads add column if not exists delivery_state    text;
alter table public.leads add column if not exists venue_name        text;

-- ─── When ───────────────────────────────────────────────────────────────
-- event_date already exists and is also populated with the delivery date so
-- existing lead views that read event_date still show something sensible.
alter table public.leads add column if not exists delivery_date     text;
alter table public.leads add column if not exists delivery_time     text;
alter table public.leads add column if not exists pickup_date       text;

-- ─── Optional index for pulling product orders out of the lead stream ───
create index if not exists leads_request_type_idx on public.leads (request_type);

-- RLS + public-insert policy are already set by schema.sql /
-- migrate_add_columns.sql; re-asserted here so this file is safe to run on
-- its own against a fresh project.
alter table public.leads enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'leads' and policyname = 'Public can submit leads'
  ) then
    create policy "Public can submit leads"
      on public.leads
      for insert
      to anon
      with check (true);
  end if;
end $$;
