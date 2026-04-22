-- Per-user sidebar ticker groups and filter state (synced from FastAPI with service role).
create table public.ticker_workspaces (
    user_id uuid not null
        primary key
        references public.profiles (id) on delete cascade,
    data jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index ticker_workspaces_updated_at_idx on public.ticker_workspaces (updated_at desc);

drop trigger if exists ticker_workspaces_set_updated_at on public.ticker_workspaces;
create trigger ticker_workspaces_set_updated_at
    before update on public.ticker_workspaces
    for each row
    execute function public.set_updated_at();

alter table public.ticker_workspaces enable row level security;

revoke all on public.ticker_workspaces from anon;
grant all on public.ticker_workspaces to service_role;
grant all on public.ticker_workspaces to authenticated;

drop policy if exists "ticker_workspaces_select_own" on public.ticker_workspaces;
create policy "ticker_workspaces_select_own"
    on public.ticker_workspaces
    for select
    to authenticated
    using (auth.uid() = user_id);

drop policy if exists "ticker_workspaces_insert_own" on public.ticker_workspaces;
create policy "ticker_workspaces_insert_own"
    on public.ticker_workspaces
    for insert
    to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "ticker_workspaces_update_own" on public.ticker_workspaces;
create policy "ticker_workspaces_update_own"
    on public.ticker_workspaces
    for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "ticker_workspaces_delete_own" on public.ticker_workspaces;
create policy "ticker_workspaces_delete_own"
    on public.ticker_workspaces
    for delete
    to authenticated
    using (auth.uid() = user_id);
