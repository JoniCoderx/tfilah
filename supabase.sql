-- tfilah.com: Supabase schema for shared readings (memorial pages, candles, Tehillim split).
--
-- HOW TO RUN: Supabase dashboard -> SQL Editor -> New query -> paste this whole file -> Run.
-- Re-running is safe: every statement is idempotent, and the file works both on an empty
-- database and on one created by an earlier version of this file (it upgrades it in place).
-- Everything runs in one transaction, so a failure leaves the database as it was.
--
-- Privacy model: a reading is link-only unless it was created with listed = true.
--   * Direct table reads (and realtime) only ever see listed, non-hidden readings.
--   * Whoever holds the link (the id) reads through get_memorial(id).
--   * Nobody writes to the tables directly; all writes go through the functions below.
--   * The id is the only secret of a link-only reading: 16 hex characters (64 bits) from the
--     database's cryptographic random source, so it cannot be guessed or enumerated.
--
-- What an anonymous visitor can still do, by design (there are no accounts): open readings,
-- light candles, and mark chapters on any reading whose link they hold (or any listed one).
-- The functions bound how much and how fast (see "limits" below); they cannot tell a vandal
-- from a reader. Moderation and clean-up queries are at the end of this file.
-- Tests: tools/test-supabase.py (needs a local Postgres, not Supabase).

begin;

-- ---------------------------------------------------------------- tables

create table if not exists public.memorials (
  id          text primary key default substr(md5(gen_random_uuid()::text), 1, 16),
  name        text not null check (char_length(name) between 1 and 60),
  parent      text not null default '' check (char_length(parent) <= 40),
  kind        text not null default 'neshama' check (kind in ('neshama','refuah','zivug','hatzlacha','general')),
  rel         text not null check (rel in ('בן','בת')),
  by_name     text not null default '' check (char_length(by_name) <= 60),
  msg         text not null default '' check (char_length(msg) <= 200),
  candles     integer not null default 1,
  done        integer not null default 0,       -- number of chapters marked done, all rounds together
  hidden      boolean not null default false,   -- set true in the dashboard to hide an abusive entry
  listed      boolean not null default false,   -- true = appears in the public list; false = link-only
  created_at  timestamptz not null default now(),
  candle_win  timestamptz not null default now(),  -- start of the current candle-counting hour
  candle_n    integer not null default 0           -- candles lit in that hour (see light_candle)
);

create table if not exists public.chapters (
  memorial_id text not null references public.memorials(id) on delete cascade,
  n           integer not null check (n between 1 and 15000),  -- chapter + 150*(round-1)
  s           text not null check (s in ('claimed','done')),
  by_name     text not null default '' check (char_length(by_name) <= 40),
  at          timestamptz not null default now(),
  primary key (memorial_id, n)
);

-- Upgrades for databases created by an earlier version of this file.
alter table public.memorials add column if not exists kind text not null default 'neshama';
-- Readings that existed before this column was added become link-only (listed = false):
-- their creators were never asked whether they wanted to be public. To put one back in the
-- public list:  update public.memorials set listed = true where id = '<id>';
alter table public.memorials add column if not exists listed boolean not null default false;
-- Multiple rounds: the key range is 1..15000 (100 rounds).
alter table public.chapters drop constraint if exists chapters_n_check;
alter table public.chapters add constraint chapters_n_check check (n between 1 and 15000);
-- Ids of new readings: 64 random bits from gen_random_uuid() (cryptographic), instead of 40 bits
-- derived from random(). Existing readings keep their shorter ids and their links keep working.
alter table public.memorials alter column id set default substr(md5(gen_random_uuid()::text), 1, 16);
-- Candle rate limit (light_candle).
alter table public.memorials add column if not exists candle_win timestamptz not null default now();
alter table public.memorials add column if not exists candle_n integer not null default 0;
-- Only if the database dates from the very first version (parent was mandatory there):
-- alter table public.memorials drop constraint if exists memorials_parent_check;

create index if not exists memorials_created_at_idx on public.memorials (created_at desc);

-- ---------------------------------------------------------------- row level security

alter table public.memorials enable row level security;
alter table public.chapters  enable row level security;

-- Direct reads see only listed, non-hidden readings. No insert/update/delete policies exist,
-- so direct writes are denied; the functions below are security definer and bypass RLS.
drop policy if exists "read memorials" on public.memorials;
create policy "read memorials" on public.memorials for select using (not hidden and listed);
drop policy if exists "read chapters" on public.chapters;
create policy "read chapters" on public.chapters for select using (
  exists (select 1 from public.memorials m where m.id = memorial_id and not m.hidden and m.listed)
);

-- Supabase grants ALL on new public tables to the API roles. Narrow that to select, so that
-- RLS is not the only thing standing between a visitor and a write (or a TRUNCATE).
revoke all on public.memorials, public.chapters from anon, authenticated;
grant select on public.memorials, public.chapters to anon, authenticated;

-- ---------------------------------------------------------------- functions

-- Signatures and return types changed since the first version, and "create or replace"
-- cannot change a return type, so drop first. (Same transaction: no window without them.)
drop function if exists public.create_memorial(text,text,text,text,text,text);
drop function if exists public.create_memorial(text,text,text,text,text,text,boolean);
drop function if exists public.get_memorial(text);
drop function if exists public.take_chapter(text,text);
drop function if exists public.claim_chapter(text,integer,text);
drop function if exists public.finish_chapter(text,integer,text);
drop function if exists public.light_candle(text);

-- ---- limits (change the numbers here if they ever get in the way) ----
--   new readings ............ 30 per 10 minutes, whole site        (create_memorial)
--   candles ................. 600 per hour per reading            (light_candle)
--   chapters marked done .... 3000 per hour per reading           (finish_chapter)
--   keys .................... only inside the reading's current round (claim/finish)
-- None of these is per visitor: Postgres never sees who is calling. A per-address limit
-- belongs in front of the database (see the notes at the end of this file).

-- Internal helpers. Not callable through the API: execute is revoked below.

-- Text typed by visitors: no control characters, no invisible or direction-override
-- characters (they can reorder or hide what is displayed), whitespace runs collapsed.
create or replace function public.tfilah_clean(t text)
returns text language sql immutable set search_path = public, pg_temp as $$
  select btrim(regexp_replace(
           regexp_replace(
             regexp_replace(coalesce(t, ''), '[\u200B-\u200F\u202A-\u202E\u2060-\u2069\uFEFF]', '', 'g'),
             '[\u0001-\u001F\u007F-\u009F]', ' ', 'g'),
           '\s+', ' ', 'g'));
$$;

-- The reading's current round: the first round whose 150 keys are not all done (1..100).
-- 101 when all 100 rounds are done.
create or replace function public.tfilah_round(p_mid text)
returns integer language plpgsql stable set search_path = public, pg_temp as $$
declare v_round integer := 1;
begin
  while v_round <= 100 and
        (select count(*) from chapters
          where memorial_id = p_mid and s = 'done'
            and n between (v_round - 1) * 150 + 1 and v_round * 150) >= 150 loop
    v_round := v_round + 1;
  end loop;
  return v_round;
end $$;

revoke all on function public.tfilah_clean(text) from public, anon, authenticated;
revoke all on function public.tfilah_round(text) from public, anon, authenticated;

create function public.create_memorial(
  p_name text, p_parent text, p_rel text, p_by text, p_msg text,
  p_kind text default 'neshama', p_listed boolean default false)
returns text language plpgsql security definer set search_path = public, pg_temp as $$
declare new_id text;
begin
  -- simple flood guard: at most 30 new pages per 10 minutes site-wide.
  -- The lock makes concurrent callers count one after another; without it a burst of
  -- parallel calls would all see "29" and all get in.
  perform pg_advisory_xact_lock(74265001);
  if (select count(*) from memorials where created_at > now() - interval '10 minutes') >= 30 then
    raise exception 'too many new pages, try again later';
  end if;
  insert into memorials(name, parent, rel, kind, by_name, msg, listed)
  values (tfilah_clean(p_name), tfilah_clean(p_parent), p_rel, coalesce(p_kind,'neshama'),
          tfilah_clean(p_by), tfilah_clean(p_msg), coalesce(p_listed, false))
  returning id into new_id;
  return new_id;
end $$;

-- The whole reading for whoever holds its id, listed or not. null if missing or hidden.
create function public.get_memorial(p_id text)
returns json language sql stable security definer set search_path = public, pg_temp as $$
  select json_build_object(
    'memorial', json_build_object(
      'id', m.id, 'name', m.name, 'parent', m.parent, 'rel', m.rel, 'kind', m.kind,
      'by_name', m.by_name, 'msg', m.msg, 'candles', m.candles, 'done', m.done,
      'listed', m.listed, 'created_at', m.created_at),
    'chapters', coalesce(
      (select json_agg(json_build_object('n', c.n, 's', c.s, 'by_name', c.by_name, 'at', c.at) order by c.n)
         from chapters c where c.memorial_id = m.id),
      '[]'::json))
  from memorials m
  where m.id = p_id and not m.hidden;
$$;

-- One more candle. At most 600 per hour per reading; beyond that the call does nothing
-- (no error), so a script cannot run the number up without end or overflow it.
create function public.light_candle(p_mid text)
returns void language sql security definer set search_path = public, pg_temp as $$
  update memorials
     set candles    = candles + 1,
         candle_n   = case when candle_win > now() - interval '1 hour' then candle_n + 1 else 1 end,
         candle_win = case when candle_win > now() - interval '1 hour' then candle_win else now() end
   where id = p_mid and not hidden
     and (candle_win <= now() - interval '1 hour' or candle_n < 600);
$$;

-- Claim one specific key. true only if THIS call got it: the key was free, or it was a claim
-- older than 24 hours (the reader walked away) which is taken over. A fresh claim by anyone,
-- including the same name, and a chapter already done, give false. So does a key beyond the
-- reading's current round: rounds open one at a time, nobody can reserve or scatter keys ahead.
create function public.claim_chapter(p_mid text, p_n integer, p_by text)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
declare v_n integer;
begin
  if p_n is null or p_n < 1 or p_n > 15000 then return false; end if;
  if (p_n - 1) / 150 + 1 > tfilah_round(p_mid) then return false; end if;
  insert into chapters(memorial_id, n, s, by_name)
  select p_mid, p_n, 'claimed', left(tfilah_clean(p_by), 40)
  where exists (select 1 from memorials where id = p_mid and not hidden)
  on conflict (memorial_id, n) do update
    set by_name = excluded.by_name, at = now()
    where chapters.s = 'claimed' and chapters.at < now() - interval '24 hours'
  returning n into v_n;
  return v_n is not null;
end $$;

-- Give the caller any free chapter of the current round and return its key, or null when
-- nothing is free (every chapter of the round is done or freshly claimed), or when the
-- reading is missing/hidden.
--   key = chapter + 150*(round-1); current round = first round whose 150 keys are not all done.
--   free = no row yet, or a claim older than 24 hours.
-- Concurrency: callers for the same reading queue on the memorial row lock, so two of them
-- can never pick the same key. claim_chapter does not take that lock, so the insert can still
-- lose to a concurrent claim of the same key; then we simply pick again.
create function public.take_chapter(p_mid text, p_by text)
returns integer language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_by    text := left(tfilah_clean(p_by), 40);
  v_round integer;
  v_base  integer;
  v_n     integer;
  v_got   integer;
begin
  perform 1 from memorials where id = p_mid and not hidden for update;
  if not found then return null; end if;

  for attempt in 1..200 loop
    v_round := tfilah_round(p_mid);
    if v_round > 100 then return null; end if;     -- 100 rounds: key space exhausted
    v_base := (v_round - 1) * 150;

    select g into v_n
      from generate_series(v_base + 1, v_base + 150) g
      left join chapters c on c.memorial_id = p_mid and c.n = g
     where c.n is null or (c.s = 'claimed' and c.at < now() - interval '24 hours')
     order by g
     limit 1;
    if v_n is null then return null; end if;

    insert into chapters(memorial_id, n, s, by_name)
    values (p_mid, v_n, 'claimed', v_by)
    on conflict (memorial_id, n) do update
      set by_name = excluded.by_name, at = now()
      where chapters.s = 'claimed' and chapters.at < now() - interval '24 hours'
    returning n into v_got;
    if v_got is not null then return v_got; end if;
    -- lost the key to a concurrent claim_chapter/finish_chapter: look again
  end loop;
  return null;
end $$;

-- Mark a key done and return the reading's new total of done chapters (all rounds).
-- Idempotent: repeating it (double click, retry after refresh) changes nothing and returns
-- the same total. Returns null, without raising, and changes nothing, for a missing/hidden
-- reading, a bad key, a key beyond the current round (a round cannot be skipped or filled in
-- advance), or when 3000 chapters of this reading were already marked in the last hour.
-- The memorial row is locked before recounting, so concurrent finishes cannot leave "done" stale.
create function public.finish_chapter(p_mid text, p_n integer, p_by text)
returns integer language plpgsql security definer set search_path = public, pg_temp as $$
declare v_done integer;
begin
  if p_n is null or p_n < 1 or p_n > 15000 then return null; end if;
  perform 1 from memorials where id = p_mid and not hidden for update;
  if not found then return null; end if;
  if (p_n - 1) / 150 + 1 > tfilah_round(p_mid) then return null; end if;
  if not exists (select 1 from chapters where memorial_id = p_mid and n = p_n and s = 'done')
     and (select count(*) from chapters
           where memorial_id = p_mid and s = 'done' and at > now() - interval '1 hour') >= 3000 then
    return null;
  end if;

  insert into chapters(memorial_id, n, s, by_name)
  values (p_mid, p_n, 'done', left(tfilah_clean(p_by), 40))
  on conflict (memorial_id, n) do update
    set s = 'done', at = now(),
        by_name = case when excluded.by_name <> '' then excluded.by_name else chapters.by_name end
    where chapters.s <> 'done';

  select count(*) into v_done from chapters where memorial_id = p_mid and s = 'done';
  update memorials set done = v_done where id = p_mid;
  return v_done;
end $$;

grant execute on function public.create_memorial(text,text,text,text,text,text,boolean) to anon, authenticated;
grant execute on function public.get_memorial(text)                  to anon, authenticated;
grant execute on function public.light_candle(text)                  to anon, authenticated;
grant execute on function public.claim_chapter(text,integer,text)    to anon, authenticated;
grant execute on function public.take_chapter(text,text)             to anon, authenticated;
grant execute on function public.finish_chapter(text,integer,text)   to anon, authenticated;

-- ---------------------------------------------------------------- realtime

-- Live updates for the public list. Realtime applies the select policies above, so link-only
-- readings are never broadcast; their pages poll get_memorial instead.
do $$
declare t text;
begin
  if not exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    raise notice 'publication supabase_realtime does not exist, skipping realtime setup';
    return;
  end if;
  foreach t in array array['memorials', 'chapters'] loop
    if not exists (select 1 from pg_publication_tables
                    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;

commit;

-- Make PostgREST pick up the new function signatures right away.
notify pgrst, 'reload schema';

-- ---------------------------------------------------------------- moderation and upkeep
-- Run these by hand in the SQL Editor when needed. Nothing below runs with the file.
--
-- Hide an abusive reading (it disappears from the list, from its link, and from every function):
--   update public.memorials set hidden = true where id = '<id>';
-- Remove an abusive name from one chapter of a reading:
--   update public.chapters set by_name = '' where memorial_id = '<id>' and n = <key>;
-- Undo vandalism (chapters falsely marked) since a given time, then recount:
--   delete from public.chapters where memorial_id = '<id>' and at > '2026-01-31 14:00+02';
--   update public.memorials m set done = (select count(*) from public.chapters c
--     where c.memorial_id = m.id and c.s = 'done') where m.id = '<id>';
-- Reset a candle count that was run up:
--   update public.memorials set candles = <number> where id = '<id>';
-- Free space: delete readings nobody touched for a year (their chapters go with them):
--   delete from public.memorials m where m.created_at < now() - interval '1 year'
--     and not exists (select 1 from public.chapters c
--                      where c.memorial_id = m.id and c.at > now() - interval '1 year');
--
-- Not covered here, because the database cannot see who is calling: a limit per visitor.
-- If the site is ever attacked through the API, the options are Supabase's own protections
-- (dashboard: Settings -> API, and "Attack Protection" under Authentication for sign-ups) or
-- routing writes through a Cloudflare function with Turnstile.
