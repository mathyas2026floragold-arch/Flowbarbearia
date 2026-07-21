begin;
create or replace function app_tenant() returns uuid language sql stable as $$select nullif(current_setting('app.barbershop_id',true),'')::uuid$$;
create or replace function app_role() returns text language sql stable as $$select nullif(current_setting('app.role',true),'')$$;

create or replace function public_create_appointment(p_slug text,p_service uuid,p_barber uuid,p_starts timestamptz,p_name text,p_phone text) returns appointments language plpgsql security definer set search_path=public as $$
declare b barbershops;s services;br barbers;c customers;a appointments;finish timestamptz;
begin
 select * into b from barbershops where slug=p_slug and status in('trial','active') for share;if not found then raise exception 'barbershop unavailable';end if;
 select * into s from services where id=p_service and barbershop_id=b.id and active and public;if not found then raise exception 'service unavailable';end if;
 if p_barber is null then select x.* into br from barbers x join barber_services bs on bs.barber_id=x.id and bs.service_id=s.id where x.barbershop_id=b.id and x.active order by x.id limit 1;else select * into br from barbers where id=p_barber and barbershop_id=b.id and active;end if;
 if not found then raise exception 'barber unavailable';end if;finish=p_starts+make_interval(mins=>s.duration_minutes+s.buffer_minutes);
 if p_starts<now() then raise exception 'past slot';end if;
 if not exists(select 1 from public_available_slots(p_slug,p_service,(p_starts at time zone b.timezone)::date,br.id) x where x.starts_at=p_starts) then raise exception 'slot not available';end if;
 if exists(select 1 from schedule_blocks x where x.barbershop_id=b.id and (x.barber_id is null or x.barber_id=br.id) and tstzrange(x.starts_at,x.ends_at,'[)')&&tstzrange(p_starts,finish,'[)')) then raise exception 'blocked';end if;
 insert into customers(barbershop_id,name,phone_e164) values(b.id,p_name,p_phone) on conflict(barbershop_id,phone_e164) do update set name=excluded.name returning * into c;
 insert into appointments(barbershop_id,customer_id,barber_id,service_id,starts_at,ends_at,status) values(b.id,c.id,br.id,s.id,p_starts,finish,'scheduled') returning * into a;
 insert into scheduled_messages(barbershop_id,customer_id,appointment_id,type,body,send_at,idempotency_key) values(b.id,c.id,a.id,'confirmation','Agendamento confirmado',now(),'appointment:'||a.id||':confirmation');return a;
end$$;

create or replace function complete_or_update_appointment(p_id uuid,p_status text,p_actor uuid) returns appointments language plpgsql security invoker as $$
declare a appointments;old appointment_status;days int;
begin
 select * into a from appointments where id=p_id and barbershop_id=app_tenant() for update;if not found then return null;end if;old=a.status;
 if p_status='completed' and old not in('arrived','in_service') then raise exception 'invalid completion transition';end if;
 update appointments set status=p_status::appointment_status,completed_at=case when p_status='completed' then now() else completed_at end,completed_by=case when p_status='completed' then p_actor else completed_by end,updated_at=now() where id=p_id returning * into a;
 insert into appointment_status_history(barbershop_id,appointment_id,from_status,to_status,actor_id) values(a.barbershop_id,a.id,old,a.status,p_actor);
 if p_status='completed' then select return_days into days from services where id=a.service_id;
  insert into scheduled_messages(barbershop_id,customer_id,appointment_id,type,body,send_at,idempotency_key) values(a.barbershop_id,a.customer_id,a.id,'thanks','Obrigado pela presença!',now(),'appointment:'||a.id||':thanks') on conflict do nothing;
  insert into scheduled_messages(barbershop_id,customer_id,appointment_id,type,body,send_at,idempotency_key) values(a.barbershop_id,a.customer_id,a.id,'reactivation','Está na hora de renovar o visual.',now()+make_interval(days=>days),'appointment:'||a.id||':reactivation') on conflict do nothing;
 elsif p_status in('cancelled','no_show') then update scheduled_messages set status='cancelled' where appointment_id=a.id and status in('pending','retry');end if;return a;
end$$;

create or replace function public_available_slots(p_slug text,p_service uuid,p_day date,p_barber uuid default null) returns table(barber_id uuid,starts_at timestamptz) language sql security definer stable as $$
with ctx as(select b.id bid,b.timezone,s.duration_minutes+s.buffer_minutes duration from barbershops b join services s on s.barbershop_id=b.id where b.slug=p_slug and s.id=p_service and b.status in('trial','active')),candidates as(select br.id barber_id,g starts_at,ctx.duration from ctx join barbers br on br.barbershop_id=ctx.bid join barber_services bs on bs.barber_id=br.id and bs.service_id=p_service join working_hours wh on wh.barbershop_id=ctx.bid and (wh.barber_id is null or wh.barber_id=br.id) and wh.weekday=extract(dow from p_day)::int cross join lateral generate_series((p_day+wh.start_time) at time zone ctx.timezone,(p_day+wh.end_time-make_interval(mins=>ctx.duration)) at time zone ctx.timezone,interval '15 minutes') g where br.active and (p_barber is null or br.id=p_barber)) select c.barber_id,c.starts_at from candidates c where c.starts_at>now() and not exists(select 1 from appointments a where a.barber_id=c.barber_id and a.status in('scheduled','confirmed','arrived','in_service') and tstzrange(a.starts_at,a.ends_at,'[)')&&tstzrange(c.starts_at,c.starts_at+make_interval(mins=>c.duration),'[)')) and not exists(select 1 from schedule_blocks x where (x.barber_id is null or x.barber_id=c.barber_id) and tstzrange(x.starts_at,x.ends_at,'[)')&&tstzrange(c.starts_at,c.starts_at+make_interval(mins=>c.duration),'[)')) order by c.starts_at$$;

create or replace function admin_create_barbershop(p_name text,p_slug text,p_email text,p_plan uuid,p_expires timestamptz,p_actor uuid) returns barbershops language plpgsql security definer set search_path=public as $$declare b barbershops;begin if app_role()<>'superadmin' then raise exception 'forbidden';end if;insert into barbershops(name,slug,status) values(p_name,p_slug,'active') returning * into b;insert into subscriptions(barbershop_id,plan_id,starts_at,expires_at,status) values(b.id,p_plan,now(),p_expires,'active');insert into audit_logs(actor_id,action,entity,entity_id,metadata) values(p_actor,'barbershop.create','barbershop',b.id,jsonb_build_object('owner_email',p_email));return b;end$$;

do $$declare t text;begin foreach t in array array['services','barbers','barber_services','working_hours','schedule_blocks','customers','appointments','appointment_status_history','whatsapp_connections','automation_rules','scheduled_messages','webhook_events'] loop execute format('alter table %I enable row level security',t);execute format('alter table %I force row level security',t);execute format('create policy tenant_isolation on %I using (barbershop_id=app_tenant()) with check (barbershop_id=app_tenant())',t);end loop;end$$;
alter table profiles enable row level security;create policy own_or_tenant_profiles on profiles using(id=auth.uid() or barbershop_id=app_tenant());
revoke all on function public_create_appointment from public;grant execute on function public_create_appointment to anon,authenticated,service_role;
revoke all on all tables in schema public from anon;grant select on barbershops,services,barbers,barber_services,working_hours to anon;
commit;
