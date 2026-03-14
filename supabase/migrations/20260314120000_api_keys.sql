create extension if not exists pgcrypto with schema extensions;

create type public.api_key_provider as enum (
    'twelvedata',
    'alphavantage',
    'massive'
);

create table public.api_keys (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    provider api_key_provider not null,
    encrypted_key bytea not null,
    key_prefix text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint api_keys_user_provider_unique unique (user_id, provider)
);

-- Index for fast lookups by user.
create index api_keys_user_id_idx on public.api_keys(user_id);

-- Audit log for key access and mutations (compliance / intrusion detection).
create table public.api_key_audit_log (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    provider api_key_provider,
    action text not null check (action in ('insert', 'update', 'delete', 'retrieve')),
    created_at timestamptz not null default now()
);

create index api_key_audit_log_user_id_idx on public.api_key_audit_log(user_id);
create index api_key_audit_log_created_at_idx on public.api_key_audit_log(created_at);

alter table public.api_key_audit_log enable row level security;

-- Users can only see their own audit entries.
create policy "api_key_audit_select_own"
    on public.api_key_audit_log
    for select
    to authenticated
    using (auth.uid() = user_id);

-- Revoke all from anon.
revoke all on public.api_keys from anon;
revoke all on public.api_key_audit_log from anon;

-- service_role (used by the backend with SUPABASE_SERVICE_ROLE_KEY) needs full access.
-- It bypasses RLS but still requires table-level grants.
grant all on public.api_keys to service_role;
grant all on public.api_key_audit_log to service_role;

-- Column-level grants: authenticated users cannot SELECT encrypted_key directly.
-- They must use get_api_key_for_use() which audits each retrieval.
revoke all on public.api_keys from authenticated;
grant select (id, user_id, provider, key_prefix, created_at, updated_at)
    on public.api_keys to authenticated;
grant insert (user_id, provider, encrypted_key, key_prefix)
    on public.api_keys to authenticated;
grant update (encrypted_key, key_prefix)
    on public.api_keys to authenticated;
grant delete on public.api_keys to authenticated;

grant select on public.api_key_audit_log to authenticated;

alter table public.api_keys enable row level security;

drop policy if exists "api_keys_select_own" on public.api_keys;
create policy "api_keys_select_own"
    on public.api_keys
    for select
    to authenticated
    using (auth.uid() = user_id);

drop policy if exists "api_keys_insert_own" on public.api_keys;
create policy "api_keys_insert_own"
    on public.api_keys
    for insert
    to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "api_keys_update_own" on public.api_keys;
create policy "api_keys_update_own"
    on public.api_keys
    for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "api_keys_delete_own" on public.api_keys;
create policy "api_keys_delete_own"
    on public.api_keys
    for delete
    to authenticated
    using (auth.uid() = user_id);

-- Audit trigger for insert/update/delete.
create or replace function public.api_key_audit_trigger()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'INSERT' then
    insert into public.api_key_audit_log (user_id, provider, action)
    values (new.user_id, new.provider, 'insert');
  elsif tg_op = 'UPDATE' then
    insert into public.api_key_audit_log (user_id, provider, action)
    values (new.user_id, new.provider, 'update');
  elsif tg_op = 'DELETE' then
    insert into public.api_key_audit_log (user_id, provider, action)
    values (old.user_id, old.provider, 'delete');
  end if;
  return coalesce(new, old);
end;
$$;

drop trigger if exists api_key_audit_trigger on public.api_keys;
create trigger api_key_audit_trigger
    after insert or update or delete on public.api_keys
    for each row execute function public.api_key_audit_trigger();

-- Only way to retrieve encrypted_key: via this function. Logs each retrieval.
create or replace function public.get_api_key_for_use(p_provider api_key_provider)
returns bytea
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid := auth.uid();
  v_encrypted bytea;
begin
  if v_user_id is null then
    raise exception 'Not authenticated';
  end if;

  select encrypted_key into v_encrypted
  from public.api_keys
  where user_id = v_user_id and provider = p_provider;

  if v_encrypted is not null then
    insert into public.api_key_audit_log (user_id, provider, action)
    values (v_user_id, p_provider, 'retrieve');
  end if;

  return v_encrypted;
end;
$$;

revoke all on function public.get_api_key_for_use(api_key_provider) from anon;
grant execute on function public.get_api_key_for_use(api_key_provider) to authenticated;

-- Enforce user_id on insert when called from a user JWT session (authenticated role).
-- When the backend inserts via service_role, auth.uid() is NULL (no sub claim in
-- service_role JWTs), so we trust the user_id the backend already provided.
create or replace function public.api_keys_enforce_user_id()
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

drop trigger if exists api_keys_enforce_user_id on public.api_keys;
create trigger api_keys_enforce_user_id
    before insert on public.api_keys
    for each row execute function public.api_keys_enforce_user_id();

-- Keep updated_at current.
drop trigger if exists set_api_keys_updated_at on public.api_keys;
create trigger set_api_keys_updated_at
    before update on public.api_keys
    for each row execute function public.set_updated_at();
