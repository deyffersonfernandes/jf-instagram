# Como a equipe trabalha (vale para todos os agentes)

Leia também: equipe/REGRAS.md (estratégia e estilo) e o manual do seu cargo.

## Ferramentas e endereços
- Central JF (artifact): `https://claude.ai/artifact/G7kmfRQ8N9jmMu9NCeN2Zp`. Coleções: `conteudos` (posts do Instagram), `whats` (PDFs do grupo do WhatsApp: titulo, status ideia|roteiro|design|pronto|agendado|enviado, roteiro, mensagem, pdf {id,nome,tamanho}, data, hora, avisadoEm), `blog` (artigos: titulo, palavraChave, status ideia|rascunho|revisao|pronto|agendado|publicado, texto, resumo, data, url), `leads` (nome, whatsapp, origem, criadoEm; dado pessoal: nunca copie para o repositório), `ideias` (banco de ideias), `modelos` (tipos de post: nome, categoria, formato, visualArte, regra, estrutura, exemplos, biblioteca), `noticias` (assuntos de notícia já usados).
- Carregue as ferramentas com ToolSearch: `select:ArtifactData` e `select:mcp__claude-code-remote__fire_trigger` (e `select:SendUserMessage` só se o CMO mandar falar direto na conversa; o normal é falar com o José pelo Telegram, via outbox/).
- Repositório: `deyffersonfernandes/jf-instagram`. Anexe com add_repo (owner deyffersonfernandes, repo jf-instagram, access "push") e clone em /home/claude/jf-instagram (se já existir, `git pull`). Commits sempre em main; se o push for recusado, `git pull --rebase` e tente de novo.
- IDs das tarefas de cada agente: equipe/agentes.json. Para acionar o próximo agente: fire_trigger com o trigger_id dele e text = `Conteúdos: id1, id2, ...` (mais uma linha `Obs: ...` se precisar).

## O post na Central (coleção conteudos)
Campos principais: titulo, categoria (alcance|identidade|competencia|oferta), modelo (mo01...), formato (Estático|Carrossel|Reel), data (AAAA-MM-DD), hora (HH:MM, Brasília), canal "instagram", status, roteiro, legenda, arquivos [{id, nome, tipo, tamanho, gerado}], arte {slides, blocos, status, geradaEm}, notas, fluxo, criadoEm, atualizadoEm.

Campo da equipe: `equipe` = {
  "etapa": "redacao" | "revisao" | "arte" | "aprovacao" | "pronto" | "agendado" | "travado",
  "tarefa": "criar" | "ajustar_cta" | "refazer",
  "briefing": "o que o CMO pediu",
  "origem": "cmo" | "jose" | "banco:<id da ideia>",
  "estilo": "frase" | "tweet" | "noticia" | "meme" | "video" | "foto",
  "urgente": true/false,
  "tentativasCopy": 0,
  "notasCopy": "motivo da devolução",
  "notasCmo": "",
  "n": número curto do post para o José citar no Telegram,
  "historico": [{"quando": ISO, "agente": "cmo|redator|copy|designer", "acao": "texto curto"}]
}

Status da Central para cada etapa (a página da Central também roda um fluxo automático; estes valores fazem a página deixar o post com a equipe):
- redacao / revisao → status "roteiro", fluxo {"estado": "equipe", "etapa": "roteiro"}
- arte / aguardando_jose → status "producao", fluxo {"estado": "equipe", "etapa": "arte"}
- aprovacao (com arte pronta) / pronto → status "pronto" (sem data), fluxo null
- agendado → status "agendado", fluxo null (a publicação automática pega de hora em hora e posta no horário)
Exceção: pedido "ajustar_cta" em post que já está "agendado" ou "pronto": não mude status nem fluxo, só a legenda e o campo equipe.

## Regras de escrita no banco
- Leia o documento (get) antes de escrever e use sempre `if_version` com a última version. Se falhar por version, leia de novo e refaça.
- Use "update" (merge), nunca "set" em documento que já existe. Sempre acrescente uma linha em equipe.historico e atualize "atualizadoEm" (agora ISO).
- Nunca mude data, hora, status de post já "postado". Nunca apague posts. Nunca publique no Instagram por outro caminho.
- Ao terminar sua parte, acione o próximo agente (fire_trigger) e termine. Não espere o próximo terminar.
- Se algo travar (ferramenta fora, erro repetido), grave equipe.etapa "travado" com o motivo em equipe.notasCmo e acione o CMO no modo APROVAR com esses ids (ele decide).
- Termine sem mensagem para o usuário: quem fala com o José é só o CMO, pelo Telegram.
