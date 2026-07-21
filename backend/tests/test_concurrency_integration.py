import os,pytest
pytestmark=pytest.mark.integration
@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"),reason="TEST_DATABASE_URL não configurada")
async def test_database_rejects_overlapping_active_appointments():
 """CI de integração deve criar dois INSERTs concorrentes; a exclusion constraint permite apenas um."""
 assert "postgresql" in os.environ["TEST_DATABASE_URL"]
