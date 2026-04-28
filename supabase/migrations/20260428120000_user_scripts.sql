-- Saved user-authored Python indicator scripts.
--
-- NOTE on safety: the runner that executes these scripts (backend.scripts.runner)
-- combines an AST allow-list, a spawned subprocess, rlimits, and a network-blocking
-- monkeypatch. That stack is not a security boundary against a determined attacker
-- with a fresh CPython escape — see todo/indicator-system.md §Security. Treat the
-- contents of public.user_scripts as untrusted input and never load it into the
-- FastAPI worker's address space.
create table public.user_scripts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    code text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint user_scripts_user_name_unique unique (user_id, name)
);

create index user_scripts_user_updated_idx
    on public.user_scripts(user_id, updated_at desc);

alter table public.user_scripts enable row level security;

revoke all on public.user_scripts from anon;
grant all on public.user_scripts to service_role;

revoke all on public.user_scripts from authenticated;
grant select on public.user_scripts to authenticated;
grant insert (name, code) on public.user_scripts to authenticated;
grant update (name, code) on public.user_scripts to authenticated;
grant delete on public.user_scripts to authenticated;

drop policy if exists "user_scripts_select_own" on public.user_scripts;
create policy "user_scripts_select_own"
    on public.user_scripts
    for select
    to authenticated
    using (auth.uid() = user_id);

drop policy if exists "user_scripts_insert_own" on public.user_scripts;
create policy "user_scripts_insert_own"
    on public.user_scripts
    for insert
    to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "user_scripts_update_own" on public.user_scripts;
create policy "user_scripts_update_own"
    on public.user_scripts
    for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "user_scripts_delete_own" on public.user_scripts;
create policy "user_scripts_delete_own"
    on public.user_scripts
    for delete
    to authenticated
    using (auth.uid() = user_id);

-- Backend inserts via service_role (auth.uid() is null); enforce user_id from
-- auth.uid() only when called from an authenticated user JWT.
create or replace function public.user_scripts_enforce_user_id()
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

drop trigger if exists user_scripts_enforce_user_id on public.user_scripts;
create trigger user_scripts_enforce_user_id
    before insert on public.user_scripts
    for each row execute function public.user_scripts_enforce_user_id();

drop trigger if exists set_user_scripts_updated_at on public.user_scripts;
create trigger set_user_scripts_updated_at
    before update on public.user_scripts
    for each row execute function public.set_updated_at();
