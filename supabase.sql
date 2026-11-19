-- tfilah.com: Supabase schema for memorial pages, candles and Tehillim split.
-- Run once in Supabase: SQL Editor -> New query -> paste -> Run.

create table if not exists public.memorials (
  id          text primary key default substr(md5(random()::text || clock_timestamp()::text), 1, 10),
  name        text not null check (char_length(name) between 1 and 60),
  parent      text not null default '' check (char_length(parent) <= 40),
  kind        text not null default 'neshama' check (kind in ('neshama','refuah','zivug','hatzlacha','general')),
  rel         text not null check (rel in ('בן','בת')),
  by_name     text not null default '' check (char_length(by_name) <= 60),
  msg         text not null default '' check (char_length(msg) <= 200),
  candles     integer not null default 1,
  done        integer not null default 0,
  hidden      boolean not null default false,   -- set true in the dashboard to hide an abusive entry
  created_at  timestamptz not null default now()
);

create table if not exists public.chapters (
  memorial_id text not null references public.memorials(id) on delete cascade,
  n           integer not null check (n between 1 and 15000),  -- chapter + 150*(round-1)
  s           text not null check (s in ('claimed','done')),
  by_name     text not null default '' check (char_length(by_name) <= 40),
  at          timestamptz not null default now(),
  primary key (memorial_id, n)
);

alter table public.memorials enable row level security;
alter table public.chapters  enable row level security;

-- Everyone can read. Nobody writes directly: all writes go through the functions below.
drop policy if exists "read memorials" on public.memorials;
create policy "read memorials" on public.memorials for select using (not hidden);
drop policy if exists "read chapters" on public.chapters;
create policy "read chapters" on public.chapters for select using (true);

create or replace function public.create_memorial(p_name text, p_parent text, p_rel text, p_by text, p_msg text, p_kind text default 'neshama')
returns text language plpgsql security definer set search_path = public as $$
declare new_id text;
begin
  -- simple flood guard: at most 30 new pages per 10 minutes site-wide
  if (select count(*) from memorials where created_at > now() - interval '10 minutes') >= 30 then
    raise exception 'too many new pages, try again later';
  end if;
  insert into memorials(name, parent, rel, kind, by_name, msg)
  values (trim(p_name), trim(coalesce(p_parent,'')), p_rel, coalesce(p_kind,'neshama'), trim(coalesce(p_by,'')), trim(coalesce(p_msg,'')))
  returning id into new_id;
  return new_id;
end $$;

create or replace function public.light_candle(p_mid text)
returns void language sql security definer set search_path = public as $$
  update memorials set candles = candles + 1 where id = p_mid and not hidden;
$$;

create or replace function public.claim_chapter(p_mid text, p_n integer, p_by text)
returns void language sql security definer set search_path = public as $$
  insert into chapters(memorial_id, n, s, by_name)
  select p_mid, p_n, 'claimed', left(trim(coalesce(p_by,'')), 40)
  where exists (select 1 from memorials where id = p_mid and not hidden)
  on conflict (memorial_id, n) do nothing;
$$;

create or replace function public.finish_chapter(p_mid text, p_n integer, p_by text)
returns void language plpgsql security definer set search_path = public as $$
begin
  insert into chapters(memorial_id, n, s, by_name)
  values (p_mid, p_n, 'done', left(trim(coalesce(p_by,'')), 40))
  on conflict (memorial_id, n) do update set s = 'done', at = now();
  update memorials set done = (select count(*) from chapters where memorial_id = p_mid and s = 'done') where id = p_mid;
end $$;

grant execute on function public.create_memorial(text,text,text,text,text,text) to anon, authenticated;
grant execute on function public.light_candle(text)                         to anon, authenticated;
grant execute on function public.claim_chapter(text,integer,text)            to anon, authenticated;
grant execute on function public.finish_chapter(text,integer,text)           to anon, authenticated;

-- Live updates (candles and chapters appear for everyone without refresh)
alter publication supabase_realtime add table public.memorials;
alter publication supabase_realtime add table public.chapters;

-- Upgrading an existing database from the first version:
-- alter table public.memorials add column if not exists kind text not null default 'neshama';
-- alter table public.memorials drop constraint if exists memorials_parent_check;
-- Upgrading for multiple rounds (the book can be completed again and again):
-- alter table public.chapters drop constraint if exists chapters_n_check;
-- alter table public.chapters add constraint chapters_n_check check (n between 1 and 15000);
