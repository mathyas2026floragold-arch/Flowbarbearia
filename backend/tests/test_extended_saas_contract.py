from pathlib import Path

ROOT=Path(__file__).parents[2]
SQL=(ROOT/"database/migrations/004_saas_complete.sql").read_text(encoding="utf-8")
AVAILABILITY=(ROOT/"database/migrations/005_public_availability_hardening.sql").read_text(encoding="utf-8")

def test_extended_operational_tables_are_tenant_scoped():
    for table in ["barbershop_units","customer_consents","schedule_breaks","holidays","waiting_list",
                  "whatsapp_conversations","whatsapp_messages","ai_settings","ai_conversation_history","notification_logs"]:
        start=SQL.index(f"create table if not exists {table}")
        end=SQL.index(");",start)
        assert "barbershop_id" in SQL[start:end],table

def test_new_tables_receive_forced_rls():
    assert "force row level security" in SQL
    assert "create policy tenant_isolation" in SQL

def test_subscription_access_gate_exists():
    dependencies=(ROOT/"backend/app/dependencies.py").read_text(encoding="utf-8")
    assert "barbershop_has_access" in SQL
    assert "barbershop_has_access" in dependencies

def test_human_handoff_disables_ai():
    tenant=(ROOT/"backend/app/routers/tenant.py").read_text(encoding="utf-8")
    assert "ai_enabled=:ai" in tenant
    assert "assigned_user_id" in tenant

def test_public_availability_is_scoped_and_honors_closures():
    assert "x.barbershop_id=c.bid" in AVAILABILITY
    assert "a.barbershop_id=c.bid" in AVAILABILITY
    assert "h.barbershop_id=c.bid" in AVAILABILITY
    assert "sb.barbershop_id=c.bid" in AVAILABILITY
    assert "barbershop_has_access(b.id)" in AVAILABILITY

def test_public_booking_revalidates_selected_barber():
    assert "public_available_slots" in AVAILABILITY
    assert "x.active and x.public" in AVAILABILITY
    assert "join barber_services" in AVAILABILITY
