from pathlib import Path
import re
ROOT=Path(__file__).parents[2]
def test_all_operational_tables_have_tenant():
 sql=(ROOT/"database/migrations/001_schema.sql").read_text()
 for name in ["services","barbers","customers","appointments","scheduled_messages","whatsapp_connections"]:
  match=re.search(rf"create table {name}\s*\((.*?)\);",sql,re.DOTALL)
  assert match, f"Tabela {name} não encontrada"
  assert "barbershop_id" in match.group(1)
def test_overlap_and_idempotency_constraints_exist():
 sql=(ROOT/"database/migrations/001_schema.sql").read_text()
 assert "no_active_overlap exclude using gist" in sql
 assert "idempotency_key text not null unique" in sql
def test_backend_never_accepts_tenant_in_operational_schema():
 schemas=(ROOT/"backend/app/schemas.py").read_text()
 assert "barbershop_id" not in schemas
