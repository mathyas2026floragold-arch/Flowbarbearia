# BarberFlow AI

SaaS multiempresa para barbearias, com três superfícies isoladas:

- `/admin/*`: superadministração da plataforma;
- `/app/*`: operação da barbearia autenticada;
- `/agendar/:slug`: agendamento público sem acesso aos dados internos.

## Stack

- React 19 + Vite (GitHub Pages)
- FastAPI + SQLAlchemy async (Northflank)
- Supabase PostgreSQL/Auth, RLS e JWT
- Gemini function calling, sempre mediado pelo backend
- Evolution API, uma instância por `barbershop_id` (um WhatsApp por barbearia)
- Worker PostgreSQL com `SKIP LOCKED`, idempotência, retry e dead-letter

## Início rápido

1. Copie `.env.example` para `.env`.
2. Execute as migrations de `database/migrations` no Supabase, na ordem.
3. Rode `docker compose up --build`.
4. Acesse o frontend em `http://localhost:5173` e a API em `http://localhost:8080/docs`.

## Segurança estrutural

O navegador nunca define o tenant de uma operação autenticada. `barbershop_id` é extraído dos claims validados do JWT e gravado na sessão PostgreSQL (`app.barbershop_id`). RLS e RBAC são camadas adicionais, e IDs enviados pelo cliente não substituem autorização.

## Conexão do WhatsApp

O proprietário ou gerente abre **WhatsApp** no painel e clica em **Conectar WhatsApp**. O backend deriva o tenant do JWT, cria a instância Evolution, registra um webhook vinculado àquela instância e devolve apenas o QR Code. Depois da leitura, todas as mensagens da barbearia usam essa conexão única. A URL e a chave da Evolution nunca são enviadas ao navegador.

Variável adicional obrigatória no backend:

```env
PUBLIC_API_URL=https://seu-backend.onrender.com
```

Para uma instalação já existente, aplique também `database/migrations/003_whatsapp_connection.sql`.

Antes de produção, configure domínios, secrets, backups/PITR, alertas, retenção LGPD e faça o checklist em `docs/PRODUCTION_CHECKLIST.md`.
