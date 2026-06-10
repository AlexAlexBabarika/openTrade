-- Saved user-authored backtest strategy scripts (params + on_bar).
--
-- Mirrors public.user_scripts (indicator scripts) as a dedicated table so
-- strategy and indicator namespaces don't collide on unique (user_id, name)
-- and the two script kinds can't be run through each other's executor.
-- Same safety note applies: treat code as untrusted input; it only ever runs
-- inside the spawn sandbox (backend.backtesting.sandbox), never in the
-- FastAPI worker's address space.
create table public.user_strategies (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    code text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint user_strategies_user_name_unique unique (user_id, name)
);

create index user_strategies_user_updated_idx
    on public.user_strategies(user_id, updated_at desc);

alter table public.user_strategies enable row level security;

revoke all on public.user_strategies from anon;
grant all on public.user_strategies to service_role;

revoke all on public.user_strategies from authenticated;
grant select on public.user_strategies to authenticated;
grant insert (name, code) on public.user_strategies to authenticated;
grant update (name, code) on public.user_strategies to authenticated;
grant delete on public.user_strategies to authenticated;

drop policy if exists "user_strategies_select_own" on public.user_strategies;
create policy "user_strategies_select_own"
    on public.user_strategies
    for select
    to authenticated
    using (auth.uid() = user_id);

drop policy if exists "user_strategies_insert_own" on public.user_strategies;
create policy "user_strategies_insert_own"
    on public.user_strategies
    for insert
    to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "user_strategies_update_own" on public.user_strategies;
create policy "user_strategies_update_own"
    on public.user_strategies
    for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "user_strategies_delete_own" on public.user_strategies;
create policy "user_strategies_delete_own"
    on public.user_strategies
    for delete
    to authenticated
    using (auth.uid() = user_id);

-- Backend inserts via service_role (auth.uid() is null); enforce user_id from
-- auth.uid() only when called from an authenticated user JWT.
create or replace function public.user_strategies_enforce_user_id()
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

drop trigger if exists user_strategies_enforce_user_id on public.user_strategies;
create trigger user_strategies_enforce_user_id
    before insert on public.user_strategies
    for each row execute function public.user_strategies_enforce_user_id();

drop trigger if exists set_user_strategies_updated_at on public.user_strategies;
create trigger set_user_strategies_updated_at
    before update on public.user_strategies
    for each row execute function public.set_updated_at();
