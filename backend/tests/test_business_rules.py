from pathlib import Path
SQL=(Path(__file__).parents[2]/"database/migrations/002_functions_rls.sql").read_text()
def test_post_service_only_on_completed():
 assert "if p_status='completed'" in SQL
 assert "elsif p_status in('cancelled','no_show')" in SQL
def test_completion_is_idempotent():
 assert SQL.count("on conflict do nothing")>=2
def test_rls_forced():
 assert "force row level security" in SQL and "barbershop_id=app_tenant()" in SQL
