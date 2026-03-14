grant all on public.api_keys to service_role;
grant all on public.api_key_audit_log to service_role;

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
