begin;

alter table plans add column if not exists monthly_price numeric(12,2);
alter table plans add column if not exists max_barbers int;
alter table plans add column if not exists max_units int not null default 1;
alter table subscriptions add column if not exists monthly_value numeric(12,2);
alter table subscriptions add column if not exists billing_day int check(billing_day between 1 and 31);
alter table subscriptions add column if not exists trial_until timestamptz;
alter table subscriptions add column if not exists grace_days int not null default 0;
alter table subscriptions add column if not exists last_renewed_at timestamptz;
alter table subscriptions add column if not exists next_billing_at timestamptz;
alter table subscriptions add column if not exists payment_method text;
alter table subscriptions add column if not exists notes text;

create table if not exists barbershop_units(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null references barbershops on delete restrict,
 name text not null,address text,phone text,timezone text not null default 'America/Fortaleza',active boolean not null default true,
 created_at timestamptz not null default now(),unique(barbershop_id,name),unique(barbershop_id,id)
);
create table if not exists customer_consents(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null references barbershops on delete restrict,
 customer_id uuid not null references customers on delete cascade,channel text not null default 'whatsapp',granted boolean not null,
 source text,recorded_at timestamptz not null default now()
);
create table if not exists schedule_breaks(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null references barbershops on delete restrict,
 barber_id uuid references barbers on delete cascade,weekday int not null check(weekday between 0 and 6),
 start_time time not null,end_time time not null,check(start_time<end_time)
);
create table if not exists holidays(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null references barbershops on delete restrict,
 unit_id uuid references barbershop_units,day date not null,name text not null,closed boolean not null default true,
 unique(barbershop_id,unit_id,day)
);
create table if not exists waiting_list(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null references barbershops on delete restrict,
 customer_id uuid references customers,customer_name text not null,phone_e164 text not null,
 service_id uuid not null references services,barber_id uuid references barbers,desired_day date not null,
 time_from time,time_to time,status text not null default 'waiting' check(status in('waiting','notified','booked','expired','cancelled')),
 created_at timestamptz not null default now()
);
create table if not exists whatsapp_conversations(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null references barbershops on delete restrict,
 customer_id uuid references customers,phone_e164 text not null,status text not null default 'new'
  check(status in('new','ai','waiting_customer','waiting_confirmation','human','booked','closed')),
 assigned_user_id uuid references profiles,ai_enabled boolean not null default true,last_message_at timestamptz,
 unread_count int not null default 0,created_at timestamptz not null default now(),updated_at timestamptz not null default now(),
 unique(barbershop_id,phone_e164)
);
create table if not exists whatsapp_messages(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null references barbershops on delete restrict,
 conversation_id uuid not null references whatsapp_conversations on delete cascade,appointment_id uuid references appointments,
 direction text not null check(direction in('inbound','outbound')),sender_type text not null check(sender_type in('customer','ai','human','system')),
 body text not null,status text not null default 'pending',provider_id text,idempotency_key text unique,error text,
 sent_at timestamptz,delivered_at timestamptz,created_at timestamptz not null default now()
);
create table if not exists ai_settings(
 id uuid primary key default gen_random_uuid(),barbershop_id uuid not null unique references barbershops on delete restrict,
 assistant_name text not null default 'Luna',tone text not null default 'natural',instructions text not null default '',
 enabled boolean not null default true,handoff_message text,updated_at timestamptz not null default now()
);
create table if not exists ai_conversation_history(
 id bigint generated always as identity primary key,barbershop_id uuid not null references barbershops on delete restrict,
 conversation_id uuid not null references whatsapp_conversations on delete cascade,role text not null,
 content text not null,function_name text,function_payload jsonb,created_at timestamptz not null default now()
);
create table if not exists notification_logs(
 id bigint generated always as identity primary key,barbershop_id uuid not null references barbershops on delete restrict,
 user_id uuid references profiles,appointment_id uuid references appointments,type text not null,status text not null,
 payload jsonb not null default '{}',created_at timestamptz not null default now()
);
create table if not exists system_settings(
 key text primary key,value jsonb not null,updated_at timestamptz not null default now(),updated_by uuid references profiles
);

create index if not exists waiting_list_match_idx on waiting_list(barbershop_id,desired_day,service_id,status);
create index if not exists conversations_recent_idx on whatsapp_conversations(barbershop_id,last_message_at desc);
create index if not exists whatsapp_messages_conversation_idx on whatsapp_messages(conversation_id,created_at);

do $$ declare t text; begin
 foreach t in array array['barbershop_units','customer_consents','schedule_breaks','holidays','waiting_list',
  'whatsapp_conversations','whatsapp_messages','ai_settings','ai_conversation_history','notification_logs'] loop
  execute format('alter table %I enable row level security',t);
  execute format('alter table %I force row level security',t);
  if not exists(select 1 from pg_policies where schemaname='public' and tablename=t and policyname='tenant_isolation') then
   execute format('create policy tenant_isolation on %I using (barbershop_id=app_tenant()) with check (barbershop_id=app_tenant())',t);
  end if;
 end loop;
end $$;

create or replace function barbershop_has_access(p_id uuid) returns boolean language sql stable security definer
set search_path=public as $$
 select exists(select 1 from barbershops b left join subscriptions s on s.barbershop_id=b.id
  where b.id=p_id and b.status in('trial','active') and (s.id is null or s.expires_at+make_interval(days=>coalesce(s.grace_days,0))>now()))
$$;

commit;
