-- Atlanta Bounce House Rentals — cart request fields on public.leads
-- Supabase project: ATLBounceHouseRentals_Leads_Board
-- Run this once in the Supabase SQL editor (https://supabase.com/dashboard/project/tbqigevoksabizjogvtm/sql/new)
--
-- Adds what's needed for a combined /cart/ request covering multiple
-- products in one submission (request_type = 'cart_request'). All the
-- contact/delivery/date columns are already shared with single-product
-- requests via migrate_product_orders.sql — this just adds the item list
-- itself. Safe to re-run: every ADD COLUMN is IF NOT EXISTS.

alter table public.leads add column if not exists cart_items  jsonb;   -- [{name, slug, qty, unit, unit_price, line_total}, ...]
alter table public.leads add column if not exists item_count  integer; -- distinct products in the cart

-- RLS + public-insert policy are already set by schema.sql /
-- migrate_product_orders.sql; re-asserted here so this file is safe to run
-- on its own against a fresh project.
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
