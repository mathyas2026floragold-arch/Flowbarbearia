from pathlib import Path
ROOT=Path(__file__).parents[2]
def test_all_operational_tables_have_tenant():
 sql=(ROOT/"database/migrations/001_schema.sql").read_text()
 for name in ["services","barbers","customers","appointments","scheduled_messages","whatsapp_connections"]:
  fragment=sql.split(f"create table {name}",1)[1].split(";",1)[0]
  assert "barbershop_id" in fragment
def test_overlap_and_idempotency_constraints_exist():
 sql=(ROOT/"database/migrations/001_schema.sql").read_text()
 assert "no_active_overlap exclude using gist" in sql
 assert "idempotency_key text not null unique" in sql
def test_backend_never_accepts_tenant_in_operational_schema():
 schemas=(ROOT/"backend/app/schemas.py").read_text()
 assert "barbershop_id" not in schemas
