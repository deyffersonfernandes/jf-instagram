# Equipe de conteúdo automática

Agentes (tarefas agendadas do Claude) que produzem os 4 posts diários do @jfernandes.trafego em cascata:

CMO (planeja) → Redator (roteiro e legenda) → Copy chief (revisa) → Designer (arte) → CMO (aprova e agenda) → publicação automática no Instagram.

- O José fala só com o CMO, pelo bot do Telegram (texto, áudio, print, vídeo). O workflow `.github/workflows/telegram.yml` lê as mensagens a cada 5 minutos (inbox/) e envia as respostas do CMO (outbox/).
- O CMO roda sozinho: planejamento às 7h37, rotina de hora em hora (minuto 8) e resumo às 21h13 (horário de Brasília). A equipe aciona o próximo agente assim que termina.
- Manuais: COMUM.md, REGRAS.md (estratégia), CMO.md, REDATOR.md, COPY.md, DESIGNER.md. IDs das tarefas: agentes.json. Estado do CMO: estado.json.
- As artes são desenhadas por `arte/render.js` com as mesmas funções da Central (`arte/funcoes.js`, gerado por `arte/extrair.py`).
