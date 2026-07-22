# Manual de rollback

## Aplicação

1. Suspenda novos deploys e registre o incidente.
2. No Render, redirecione o tráfego para a imagem anterior imutável.
3. No GitHub Pages, reverta o commit do frontend e aguarde o workflow.
4. Se o formato das mensagens mudou, pause o worker antes do rollback.
5. Valide `/health`, login, isolamento e um agendamento de teste.

## Banco

Migrations devem ser aditivas e compatíveis com a versão anterior. Prefira uma migration corretiva. Antes de qualquer reversão destrutiva, tire snapshot e confirme o backup. `database/rollback/full_rollback.sql` remove todo o domínio e serve apenas para ambientes descartáveis; não deve ser executado em produção com dados.

## Fila e integrações

Pause o worker, preserve itens `pending/retry/dead`, reverta a API, reative um único worker e reprocese pela chave de idempotência. Nunca limpe a fila para resolver duplicidade.
