# Evolution API no Render (ambiente de demonstração)

Este diretório faz parte do mesmo projeto BarberFlow. Ele apenas descreve o segundo Web Service necessário para hospedar a Evolution API.

No Render, crie um Web Service Docker apontando o diretório raiz para `evolution-render` e defina `PORT=8080`. Configure também, diretamente no painel, as variáveis oficiais da Evolution para PostgreSQL, Redis e `AUTHENTICATION_API_KEY`.

O serviço gratuito adormece e não possui disco persistente. Use esta configuração somente para demonstração. Para produção, use instância paga com persistência e mantenha PostgreSQL e Redis externos.
