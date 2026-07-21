# Checklist de produção

- [ ] Aplicar migrations em staging e executar testes de concorrência/isolamento.
- [ ] Configurar Supabase Auth, URLs autorizadas, MFA de superadmins e rotação de tokens.
- [ ] Confirmar que `service_role`, Gemini, Evolution e chaves de criptografia existem somente na Northflank.
- [ ] Ativar PITR/backups e testar restauração.
- [ ] Configurar uma instância Evolution exclusiva por barbearia e webhook HMAC.
- [ ] Validar CORS com os domínios exatos; nunca usar `*` com credenciais.
- [ ] Ativar rate limiting no edge/Northflank para login, público e webhook.
- [ ] Criar alertas de API, banco, filas atrasadas, dead-letter e WhatsApp offline.
- [ ] Validar consentimento, opt-out, retenção e procedimentos LGPD.
- [ ] Executar SAST, auditoria de dependências e teste de invasão antes da venda.
- [ ] Confirmar runbook e rollback em ensaio de staging.
