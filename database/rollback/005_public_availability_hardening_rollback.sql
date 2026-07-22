begin;

create or replace function public_available_slots(p_slug text,p_service uuid,p_day date,p_barber uuid default null)
returns table(barber_id uuid,starts_at timestamptz) language sql security definer stable as $$
 with ctx as(select b.id bid,b.timezone,s.duration_minutes+s.buffer_minutes duration from barbershops b join services s on s.barbershop_id=b.id where b.slug=p_slug and s.id=p_service and b.status in('trial','active')),
 candidates as(select br.id barber_id,g starts_at,ctx.duration from ctx join barbers br on br.barbershop_id=ctx.bid join barber_services bs on bs.barber_id=br.id and bs.service_id=p_service join working_hours wh on wh.barbershop_id=ctx.bid and (wh.barber_id is null or wh.barber_id=br.id) and wh.weekday=extract(dow from p_day)::int cross join lateral generate_series((p_day+wh.start_time) at time zone ctx.timezone,(p_day+wh.end_time-make_interval(mins=>ctx.duration)) at time zone ctx.timezone,interval '15 minutes') g where br.active and (p_barber is null or br.id=p_barber))
 select c.barber_id,c.starts_at from candidates c where c.starts_at>now()
 and not exists(select 1 from appointments a where a.barber_id=c.barber_id and a.status in('scheduled','confirmed','arrived','in_service') and tstzrange(a.starts_at,a.ends_at,'[)')&&tstzrange(c.starts_at,c.starts_at+make_interval(mins=>c.duration),'[)'))
 and not exists(select 1 from schedule_blocks x where (x.barber_id is null or x.barber_id=c.barber_id) and tstzrange(x.starts_at,x.ends_at,'[)')&&tstzrange(c.starts_at,c.starts_at+make_interval(mins=>c.duration),'[)')) order by c.starts_at
$$;

commit;
