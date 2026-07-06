-- Atlanta Bounce House Rentals — patch an existing leads table
-- Run this in the Supabase SQL editor if you already had a "leads" table
-- before running schema.sql, so it's missing columns the wizard sends
-- (e.g. "Could not find the 'chair_count' column of 'leads' in the schema cache").
-- Safe to run multiple times — every ADD COLUMN is IF NOT EXISTS.

alter table public.leads add column if not exists event_type   text;
alter table public.leads add column if not exists services     text[];
alter table public.leads add column if not exists event_date   text;
alter table public.leads add column if not exists zip_code     text;
alter table public.leads add column if not exists guest_count  text;
alter table public.leads add column if not exists chair_count  text;
alter table public.leads add column if not exists chair_style  text;
alter table public.leads add column if not exists table_count  text;
alter table public.leads add column if not exists needs_tent   text;
alter table public.leads add column if not exists concessions  text[];
alter table public.leads add column if not exists name         text;
alter table public.leads add column if not exists phone        text;
alter table public.leads add column if not exists email        text;
alter table public.leads add column if not exists message      text;
alter table public.leads add column if not exists source       text;
alter table public.leads add column if not exists page_url     text;
alter table public.leads add column if not exists created_at   timestamptz not null default now();

-- Make sure RLS + the public-insert policy are in place too.
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
