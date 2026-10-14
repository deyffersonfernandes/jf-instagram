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
| `IG_TOKEN` | token de acesso gerado no app da Meta (login do Instagram), com `instagram_business_content_publish` |
| `IG_USER_ID` | *(opcional)* ID da conta; se faltar, é descoberto pelo token |
| `GRAPH_HOST` | *(opcional)* use `graph.facebook.com` só se o token for do login do Facebook; o padrão é `graph.instagram.com` |

Teste manual: **Actions → Publicar no Instagram → Run workflow**. O log mostra a conta conectada (`Conta conectada: @...`) mesmo com a fila vazia.


## Seguidores (meta da Central JF)

- `.github/workflows/seguidores.yml` roda a cada 30 minutos (aos 17 e 47) e chama `seguidores.py`.
- `seguidores.py` lê `followers_count` pela API oficial do Instagram (mesmo `IG_TOKEN` do publicador) e grava `seguidores.json`. Só faz commit quando o número muda.
- A tarefa agendada "Atualizar seguidores Central JF (Instagram)" lê esse arquivo toda hora (aos 52) e atualiza a meta "Seguidores no Instagram" na Central JF.
- Se o token vencer, a leitura para e a tarefa avisa depois de 3 horas sem leitura.
