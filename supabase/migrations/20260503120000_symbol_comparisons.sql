-- Per-user symbol comparisons overlaid on a main chart symbol.
-- See todo/symbol-comparison-design.md.

create table public.symbol_comparisons (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references auth.users(id) on delete cascade,
    main_symbol       text not null,
    comparison_symbol text not null,
    provider          text not null,
    color             text not null,
    series_type       text not null check (series_type in ('line', 'candlestick')),
    position          int  not null default 0,
    created_at        timestamptz not null default now(),
    constraint symbol_comparisons_unique unique (user_id, main_symbol, comparison_symbol)
);

create index symbol_comparisons_user_main_idx
    on public.symbol_comparisons (user_id, main_symbol);

alter table public.symbol_comparisons enable row level security;

revoke all on public.symbol_comparisons from anon;
grant all on public.symbol_comparisons to service_role;

revoke all on public.symbol_comparisons from authenticated;
grant select on public.symbol_comparisons to authenticated;
grant insert (main_symbol, comparison_symbol, provider, color, series_type, position)
    on public.symbol_comparisons to authenticated;
grant update (color, series_type, position) on public.symbol_comparisons to authenticated;
grant delete on public.symbol_comparisons to authenticated;

drop policy if exists "symbol_comparisons_select_own" on public.symbol_comparisons;
create policy "symbol_comparisons_select_own"
    on public.symbol_comparisons
    for select
    to authenticated
    using (auth.uid() = user_id);

drop policy if exists "symbol_comparisons_insert_own" on public.symbol_comparisons;
create policy "symbol_comparisons_insert_own"
    on public.symbol_comparisons
    for insert
    to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "symbol_comparisons_update_own" on public.symbol_comparisons;
create policy "symbol_comparisons_update_own"
    on public.symbol_comparisons
    for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "symbol_comparisons_delete_own" on public.symbol_comparisons;
create policy "symbol_comparisons_delete_own"
    on public.symbol_comparisons
    for delete
    to authenticated
    using (auth.uid() = user_id);

-- Backend inserts via service_role (auth.uid() is null); enforce user_id from
-- auth.uid() only when called from an authenticated user JWT.
create or replace function public.symbol_comparisons_enforce_user_id()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is not null then
    new.user_id := auth.uid();
  end if;
  return new;
end;
$$;

drop trigger if exists symbol_comparisons_enforce_user_id on public.symbol_comparisons;
create trigger symbol_comparisons_enforce_user_id
    before insert on public.symbol_comparisons
    for each row execute function public.symbol_comparisons_enforce_user_id();
