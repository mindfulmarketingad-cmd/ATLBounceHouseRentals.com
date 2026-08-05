-- Atlanta Bounce House Rentals — booking wizard leads table
-- Supabase project: ATLBounceHouseRentals_Leads_Board
-- Run this once in the Supabase SQL editor (https://supabase.com/dashboard/project/tbqigevoksabizjogvtm/sql/new)

create extension if not exists pgcrypto;

create table if not exists public.leads (
  id            uuid primary key default gen_random_uuid(),
  event_type    text,
  services      text[],
  event_date    text,
  zip_code      text,
  guest_count   text,
  chair_count   text,
  chair_style   text,
  table_count   text,
  needs_tent    text,
  concessions   text[],
  name          text,
  phone         text,
  email         text,
  message       text,
  source        text,
  page_url      text,
  created_at    timestamptz not null default now()
);

alter table public.leads enable row level security;

-- Allow the public "anon" key to INSERT leads from the website, but not
-- read/update/delete them back out — keeps customer data private even
-- though the anon key is exposed in client-side JS.
create policy "Public can submit leads"
  on public.leads
  for insert
  to anon
  with check (true);
