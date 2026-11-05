# Roteiro de Reels IA (formato que o estúdio entende)

O roteiro é um JSON com a narração dividida em **falas** (frases curtas, na ordem em que o José fala). Cada fala pode **abrir uma cena** (`cena`) e/ou **acrescentar um passo** à cena atual (`passo`, um objeto ou uma lista). O passo acontece quando a fala começa; com `"em": "palavra"` ele acontece exatamente quando essa palavra é dita; `"atraso": 0.5` empurra meio segundo.

```json
{
  "titulo": "Vou pensar",
  "formato": "chat",
  "tema": "escuro",
  "destaques": ["pensar", "acompanhamento"],
  "final": {"titulo": "Segue para a parte 2", "sub": "Marketing e vendas para nutricionistas"},
  "falas": [
    {"texto": "A paciente mandou: vou pensar.", "cena": {"tipo": "chat", "contato": "Paciente · Ana"},
     "passo": {"de": "ele", "msg": "Vi o valor. Vou pensar e te aviso 🙂", "hora": "14:02"}},
    {"texto": "E você respondeu assim.", "passo": {"de": "eu", "msg": "Tudo bem! Qualquer coisa me chama.", "lido": true, "marca": "erro"}}
  ]
}
```

- `tema`: `escuro` (padrão), `claro` ou `noite`.
- `destaques`: palavras que ficam amarelas na legenda (2 a 6 palavras-chave).
- `final`: card final com a foto e o @ (sai sozinho no fim; use `"final": null` para não ter).
- Em qualquer texto de tela, `*palavra*` fica amarela.
- Cores aceitas: `hi` (amarelo), `ruim` (vermelho), `bom` (verde), `acc` (verde-água), `azul`, `roxo`, `laranja`, `txt`, `branco`.
- A legenda (palavra por palavra) é sempre a própria fala: não repita a fala inteira na tela. A tela mostra o desenho, números, rótulos curtos.

## Passo que vale em qualquer cena
`{"selo": "SUMIU", "cor": "ruim"}`: carimbo inclinado no topo da cena (ex.: FECHOU, SUMIU, VÁCUO, AGENDA SANFONA). Som de acerto ou erro conforme a cor.

## Cenas

| tipo | dados da cena | passos |
|---|---|---|
| `titulo` | — | `{"texto": "Isso é *recorrência*.", "cor": "txt", "icone": "check"}` empilha até 3 linhas; ícones: check, x, relogio, pessoa, dinheiro, coracao, alerta, seta, calendario, celular, grafico |
| `frase` | `fundo` (cor, padrão preto) | `{"texto": "Você não tem problema de *agenda*."}` troca a frase (estilo Apple, cortes secos) |
| `chat` | `contato`, `status` | `{"de": "ele"/"eu", "msg": "...", "hora": "14:02", "lido": true, "marca": "erro"/"acerto"}` · `{"aviso": "Ana visualizou e não respondeu"}` · `{"online": "visto por último ontem"}` |
| `conta` | `titulo`, `prefixo` ("R$ "), `sufixo` | `{"rotulo": "5 retornos", "valor": 1250, "op": "+"}` (número conta até o valor) · `{"total": 4650, "rotulo": "Você perdeu", "cor": "ruim"}` |
| `barras` | `titulo`, `prefixo`, `sufixo`, `ordenar` (true = corrida), `barras`: [{"nome", "valor", "cor"}] | `{"mostrar": "todas"}` ou `{"mostrar": 0}` · `{"valores": [3200, 9600], "rotulo": "DEZEMBRO"}` anima para os novos valores · `{"destacar": 1}` |
| `split` | `esq`: {"titulo", "cor"}, `dir`: {"titulo", "cor"} (esq = erro, dir = acerto) | `{"lado": "esq", "texto": "Manda o preço seco"}` · `{"resultado": {"esq": "Vácuo", "dir": "Fechou"}}` |
| `quiz` | `pergunta`, `opcoes` (2 a 4), `certa` (índice) | `{"acao": "timer", "seg": 3}` · `{"acao": "revelar"}` · `{"explica": "Valor primeiro, preço depois."}` |
| `tier` | `titulo`, `faixas` (padrão S A B C D) | `{"item": "Indicação", "faixa": "B"}` |
| `top` | `titulo` | `{"n": 3, "texto": "Ninguém marcou o retorno"}` (contagem regressiva: 3, 2, 1) |
| `mito` | — | `{"frase": "Consulta barata enche a agenda"}` · `{"veredito": "MITO"}` ou `"VERDADE"` · `{"verdade": "Preço baixo atrai quem compara preço."}` (o card vira) |
| `agenda` | `titulo`, `dias` (lista ou número), `horas` (padrão 8), `cheios` (já ocupados) | `{"encher": 18, "cor": "bom"}` · `{"esvaziar": 10}` · `{"rotulo": "Agenda sanfona", "cor": "ruim"}` |
| `jogo` | `nome`, `vida` (0 a 100), `rotulo` (padrão PACIENTES ATIVOS), `nivel` | `{"delta": -30, "texto": "Não chamou o paciente de volta"}` · `{"nivel": 2}` · `{"fim": "GAME OVER"}` |
| `plantao` | `tag` (PLANTÃO, URGENTE), `letreiro` | `{"manchete": "..."}` |
| `timeline` | `titulo` | `{"marco": "Dia 7", "texto": "Ele some", "cor": "ruim"}` |
| `funil` | `etapas`: [{"nome", "valor"}] , `prefixo`, `sufixo` | `{"mostrar": 0}` (uma etapa por vez) |
| `celular` | `hora`, `data` | `{"notif": {"app": "WhatsApp"/"Instagram"/"Agenda"/"Banco", "titulo": "...", "texto": "..."}}` · `{"numero": 12000, "rotulo": "seguidores", "prefixo": "", "cor": "hi"}` |
| `antes_depois` | `antes`: {"titulo", "linhas": [...]}, `depois`: {...} | `{"revelar": true}` (a cortina passa) |
| `final` | `titulo`, `sub` | — (card com foto e @) |

## Regras de ritmo
- 35 a 60 segundos de fala (90 a 150 palavras). Falas curtas: 4 a 14 palavras.
- A primeira fala é o gancho e já abre uma cena com algo na tela no primeiro segundo.
- Troque a cena ou acrescente um passo a cada 2 a 5 segundos (toda fala tem `cena` ou `passo`).
- Use 2 a 5 cenas diferentes por vídeo, sempre ligadas ao formato escolhido.
- Números só reais ou claramente de exemplo ("se você cobra R$ 300..."). Nunca invente pesquisa, estatística ou caso.
- Fala em português do Brasil, como o José fala: direto, frases curtas, "você".
- A última fala fecha a ideia (nome da lição, virada ou CTA curto: "Manda para uma amiga nutri que precisa ver isso."). Nada de e-book nem desconto.
