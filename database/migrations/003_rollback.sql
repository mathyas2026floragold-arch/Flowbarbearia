-- Executar somente durante rollback destrutivo e após backup verificado.
begin;
drop function if exists admin_create_barbershop(text,text,text,uuid,timestamptz,uuid);
drop function if exists public_available_slots(text,uuid,date,uuid);
drop function if exists complete_or_update_appointment(uuid,text,uuid);
drop function if exists public_create_appointment(text,uuid,uuid,timestamptz,text,text);
drop table if exists webhook_events,scheduled_messages,automation_rules,whatsapp_connections,appointment_status_history,appointments,customers,schedule_blocks,working_hours,barber_services,barbers,services,audit_logs,profiles,subscriptions,barbershops,plans cascade;
drop type if exists message_status,appointment_status,barbershop_status;
commit;
