import os
os.environ.setdefault("DATABASE_URL","postgresql+asyncpg://postgres:postgres@localhost/test")
os.environ.setdefault("EVOLUTION_WEBHOOK_SECRET","test-secret")
