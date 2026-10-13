# jf-instagram

Publicação automática no Instagram a partir do calendário da **Central JF**.

## Como funciona

1. **Toda hora**, uma tarefa agendada do Claude lê a Central JF e pega os posts com status *Agendado*, data, horário e arquivo que vencem nas próximas 2 horas.
2. Ela converte as imagens para o formato que o Instagram aceita (JPEG, proporção entre 4:5 e 1,91:1) e coloca cada post em `fila/<id>/`.
3. **A cada 10 minutos**, o GitHub Actions confere a fila e publica pela API oficial da Meta o que já chegou no horário (imagem única, carrossel ou Reel).
4. O resultado vai para `publicados/` (ou `erros/`), e na rodada seguinte o Claude marca o post como **Postado** na Central.

## Regras de segurança

- Post com horário vencido há mais de 6 horas não é publicado. Ele vai para `erros/`, para não sair nada fora de hora.
- Um erro é tentado 3 vezes. Depois disso, o post vai para `erros/` com o motivo.
- Criativos marcados só como *Anúncio* e posts do YouTube são ignorados.
- O token da Meta fica só nos **Secrets** do repositório, nunca nos arquivos.

## Configuração (uma vez)

Em **Settings → Secrets and variables → Actions → New repository secret**:

| Nome | Valor |
|---|---|
| `IG_USER_ID` | ID da conta profissional do Instagram |
| `IG_TOKEN` | token de acesso gerado no app da Meta (login do Instagram), com `instagram_business_content_publish` |
| `GRAPH_HOST` | *(opcional)* use `graph.facebook.com` só se o token for do login do Facebook; o padrão é `graph.instagram.com` |

Teste manual: **Actions → Publicar no Instagram → Run workflow**.
