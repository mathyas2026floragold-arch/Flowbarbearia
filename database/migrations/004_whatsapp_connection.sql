-- Upgrade para instalações que já aplicaram 001_schema.sql.
alter table whatsapp_connections add column if not exists phone_number text;
alter table whatsapp_connections add column if not exists created_at timestamptz not null default now();
alter table whatsapp_connections drop constraint if exists whatsapp_connections_status_check;
alter table whatsapp_connections add constraint whatsapp_connections_status_check
  check(status in('offline','connecting','connected'));
