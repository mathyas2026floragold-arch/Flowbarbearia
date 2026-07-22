begin;

create or replace function public_available_slots(
 p_slug text,p_service uuid,p_day date,p_barber uuid default null
) returns table(barber_id uuid,starts_at timestamptz)
language sql security definer stable set search_path=public as $$
 with ctx as(
  select b.id bid,b.timezone,s.duration_minutes+s.buffer_minutes duration
  from barbershops b join services s on s.barbershop_id=b.id
  where b.slug=p_slug and s.id=p_service and s.active and s.public
    and barbershop_has_access(b.id)
 ), candidates as(
  select ctx.bid,ctx.timezone,br.id barber_id,g starts_at,ctx.duration
  from ctx
  join barbers br on br.barbershop_id=ctx.bid
  join barber_services bs on bs.barber_id=br.id and bs.service_id=p_service
  join working_hours wh on wh.barbershop_id=ctx.bid
    and (wh.barber_id is null or wh.barber_id=br.id)
    and wh.weekday=extract(dow from p_day)::int
  cross join lateral generate_series(
   (p_day+wh.start_time) at time zone ctx.timezone,
   (p_day+wh.end_time-make_interval(mins=>ctx.duration)) at time zone ctx.timezone,
   interval '15 minutes'
  ) g
  where br.active and br.public and (p_barber is null or br.id=p_barber)
 )
 select distinct c.barber_id,c.starts_at
 from candidates c
 where c.starts_at>now()
  and not exists(
   select 1 from holidays h where h.barbershop_id=c.bid and h.day=p_day and h.closed
  )
  and not exists(
   select 1 from schedule_breaks sb
   where sb.barbershop_id=c.bid and (sb.barber_id is null or sb.barber_id=c.barber_id)
    and sb.weekday=extract(dow from p_day)::int
    and tsrange(p_day+sb.start_time,p_day+sb.end_time,'[)') &&
        tsrange((c.starts_at at time zone c.timezone)::timestamp,
                (c.starts_at at time zone c.timezone)::timestamp+make_interval(mins=>c.duration),'[)')
  )
  and not exists(
   select 1 from appointments a
   where a.barbershop_id=c.bid and a.barber_id=c.barber_id
    and a.status in('scheduled','confirmed','arrived','in_service')
    and tstzrange(a.starts_at,a.ends_at,'[)') &&
        tstzrange(c.starts_at,c.starts_at+make_interval(mins=>c.duration),'[)')
  )
  and not exists(
   select 1 from schedule_blocks x
   where x.barbershop_id=c.bid and (x.barber_id is null or x.barber_id=c.barber_id)
    and tstzrange(x.starts_at,x.ends_at,'[)') &&
        tstzrange(c.starts_at,c.starts_at+make_interval(mins=>c.duration),'[)')
  )
 order by c.starts_at;
$$;

revoke all on function public_available_slots(text,uuid,date,uuid) from public;
grant execute on function public_available_slots(text,uuid,date,uuid) to anon,authenticated,service_role;

create or replace function public_create_appointment(
 p_slug text,p_service uuid,p_barber uuid,p_starts timestamptz,p_name text,p_phone text
) returns appointments language plpgsql security definer set search_path=public as $$
declare b barbershops;s services;br barbers;c customers;a appointments;finish timestamptz;
begin
 select * into b from barbershops where slug=p_slug and barbershop_has_access(id) for share;
 if not found then raise exception 'barbershop unavailable';end if;
 select * into s from services where id=p_service and barbershop_id=b.id and active and public;
 if not found then raise exception 'service unavailable';end if;
 if p_barber is null then
  select x.* into br from barbers x join barber_services bs on bs.barber_id=x.id and bs.service_id=s.id
  where x.barbershop_id=b.id and x.active and x.public order by x.id limit 1;
 else
  select x.* into br from barbers x join barber_services bs on bs.barber_id=x.id and bs.service_id=s.id
  where x.id=p_barber and x.barbershop_id=b.id and x.active and x.public;
 end if;
 if not found then raise exception 'barber unavailable';end if;
 finish=p_starts+make_interval(mins=>s.duration_minutes+s.buffer_minutes);
 if p_starts<now() then raise exception 'past slot';end if;
 if not exists(select 1 from public_available_slots(p_slug,p_service,(p_starts at time zone b.timezone)::date,br.id) x where x.starts_at=p_starts)
  then raise exception 'slot not available';end if;
 insert into customers(barbershop_id,name,phone_e164) values(b.id,p_name,p_phone)
 on conflict(barbershop_id,phone_e164) do update set name=excluded.name returning * into c;
 insert into appointments(barbershop_id,customer_id,barber_id,service_id,starts_at,ends_at,status)
 values(b.id,c.id,br.id,s.id,p_starts,finish,'scheduled') returning * into a;
 insert into scheduled_messages(barbershop_id,customer_id,appointment_id,type,body,send_at,idempotency_key)
 values(b.id,c.id,a.id,'confirmation','Agendamento confirmado',now(),'appointment:'||a.id||':confirmation');
 return a;
end$$;

revoke all on function public_create_appointment(text,uuid,uuid,timestamptz,text,text) from public;
grant execute on function public_create_appointment(text,uuid,uuid,timestamptz,text,text) to anon,authenticated,service_role;

commit;
