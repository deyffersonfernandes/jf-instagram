# Roteiro de Reels IA (formato que o estúdio entende)

O modelo dos vídeos é o do "Como atrair pacientes pelo Instagram": **um tema prático ensinado do começo ao fim, e tudo o que a fala cita aparece sendo montado na tela do app** (perfil, WhatsApp, Stories, página de links, consultório). O roteiro é uma corrente **problema → solução → novo problema → solução → CTA** ("Mas tem um problema… Então você… Pronto! Agora… Só que…").

O roteiro é um JSON com a narração dividida em **falas** (frases curtas, na ordem em que o José fala). Cada fala pode **abrir uma cena** (`cena`) e/ou **acrescentar um passo** à cena atual (`passo`, um objeto ou uma lista). O passo acontece quando a fala começa; com `"em": "palavra"` ele acontece exatamente quando essa palavra é dita; `"atraso": 0.5` empurra meio segundo.

```json
{
  "titulo": "A bio que vende",
  "estilo": "tela",
  "velocidade": 1.1,
  "tema": "claro",
  "final": null,
  "destaques": ["clara", "próximo"],
  "falas": [
    {"texto": "Você é nutricionista e cria um Instagram para atrair pacientes.", "cena": {"tipo": "consultorio"}, "passo": {"pensa": "Como atrair pacientes pelo Instagram? 🤔"}},
    {"texto": "Mas tem um problema: sua bio só diz “Nutricionista clínica”.", "cena": {"tipo": "perfil", "usuario": "anasouzanutri", "nome": "Ana Souza", "foto": true, "bio": "Nutricionista clínica", "grade": 6}, "passo": {"rotulo": "SÓ ISSO?", "alvo": "bio", "em": "bio"}},
    {"texto": "Então você troca por uma frase clara.", "cena": {"tipo": "editar", "nome": "Ana Souza", "foto": true}, "passo": {"set": {"bio": "Ajudo mulheres a emagrecer com acompanhamento nutricional"}, "em": "troca"}},
    {"texto": "Salva esse vídeo e confere sua bio hoje.", "cena": {"tipo": "cta", "modo": "salvar", "post": "Confere sua bio hoje"}}
  ]
}
```

- Sempre `"estilo": "tela"`, `"tema": "claro"`, `"velocidade": 1.1` e `"final": null` (o fim é a cena `cta`). Todo vídeo sai com a voz acelerada para 1.1 (`"acelerar": 1.1` é o padrão do render com áudio); o José gera a voz no ElevenLabs em velocidade normal.
- `destaques`: 2 a 4 palavras da fala que ficam amarelas na legenda (a legenda é uma palavra por vez, no meio da tela).
- `legenda_y` (opcional): altura da legenda (padrão 1330). Use 1720 quando a parte de baixo da tela for importante (ex.: grade de posts).
- A personagem é sempre a mesma nutri: **Ana Souza** (@anasouzanutri, loira, de jaleco, "Ajudo mulheres a emagrecer com acompanhamento nutricional").

## Passos que valem em qualquer cena de tela
- `{"problema": "Esse atendimento é pra mim?"}`: notificação vermelha que cai do topo com o problema (fica uns 3 s). Escreva como a dúvida de quem vê o perfil.
- `{"resolvido": "Agora ela sabe para quem é"}`: a mesma faixa, verde.
- `{"rotulo": "QUEM VOCÊ AJUDA", "alvo": "bio"}`: moldura amarela no elemento + etiqueta embaixo (`lado`: "d", "e" ou "c").
- `{"tap": "link"}`: o dedo tocando no elemento.
- `{"notif": {"app": "WhatsApp"/"Instagram"/"Agenda", "titulo": "Nova consulta", "texto": "Ter, 14:00"}}`: notificação do celular.
- `{"comemora": "BIO PRONTA!", "y": 760}`: confete e título amarelo grande (o "perfil completo" do vídeo de referência).
- `{"glitch": true}`: tremida de tela (para o falso final "ou quase…").
- `{"selo": "FECHOU", "cor": "bom"}`: carimbo.

## Cenas de tela

| tipo | dados | passos |
|---|---|---|
| `consultorio` | — | `{"pensa": "Como atrair pacientes? 🤔"}` · `{"fala": "Aqui está seu plano!"}` (`"quem": "paciente"` para o balão da paciente) · `{"paciente": "entra"/"senta"/"sai"}` · `{"agenda": 0}` (quadro da agenda na parede com N horários cheios, ou "cheia") · `{"popup": {"titulo": "Datas para o retorno", "linhas": ["Qui 14/11 · 15h"]}}` |
| `perfil` | `usuario`, `nome`, `foto`, `verificado`, `posts`, `seguidores`, `seguindo`, `crn`, `bio`, `cta`, `link`, `botao`, `destaques` (lista), `fixados` (lista de títulos), `grade` (quantos posts) | `{"set": {"bio": "..."}}` muda qualquer campo (texto aparece sendo digitado; números contam). Alvos para rotulo/tap: usuario, foto, nome, seguidores, crn, bio, cta, link, editar, botao, destaques, grade, fixado0, fixado1, fixado2 |
| `editar` | `nome`, `usuario`, `bio`, `links`, `foto` | `{"set": {"bio": "..."}}` digita no campo com cursor. Alvos: foto, nome, usuario, bio, links |
| `whats` | `contato`, `status` | `{"de": "ele", "msg": "Quanto custa?", "hora": "18:02"}` (aparece "digitando...") · `{"de": "eu", "msg": "...", "lido": true, "marca": "erro"/"acerto"}` (é digitada na caixa e enviada; `"digitar": false` para já estar na conversa) · `{"aviso": "Juliana visualizou"}`. Para mensagens que já estavam na conversa no começo da cena, use `"digitando": false`/`"digitar": false` e `"som": ""` |
| `stories` | `vazio` (texto da tela antes do 1º story) | `{"story": {"tipo": "texto"/"foto"/"bastidor"/"caixinha"/"link", "texto": "...", "titulo": "...", "objeto": "cafe"/"mesa", "cor1": "#F58529", "cor2": "#DD2A7B"}}` abre um story novo · `{"grade": true}` mostra todos lado a lado (começo, meio e fim) |
| `links` | `nome`, `botoes` (lista) | `{"botoes": [...]}` troca os botões · `{"destaque": 0}` deixa o botão grande e verde · tap em "botao0" |
| `conteudos` | `carrossel` (título do carrossel) | `{"duvida": "Preciso cortar pão?"}` · `{"mostrar": "reels"/"carrossel"/"stories"}` |
| `caminho` | `titulo`, `etapas`: [{"nome", "icone", "rotulo"}] | `{"etapa": 0}` acende a etapa (mundinho com caminho de hexágonos, como o "consultório previsível") · `{"final": true}` mostra o título |
| `cta` | `modo` "comentar" (com `palavra`: QUERO, STORIES, IDEIAS…) ou "salvar" (com `post`: a frase do post salvo) | — (aba de comentários enchendo com a palavra, ou o post sendo salvo) |

Também existem as cenas antigas (`quiz`, `agenda`, `barras`, `split`, `titulo`, `chat`...) para um momento pontual (ex.: `quiz` para "escolha um público").

## Regras de ritmo
- 20 a 45 segundos de fala (60 a 120 palavras), como os roteiros do José.
- A primeira fala já abre uma cena com algo na tela no primeiro segundo ("Você é nutricionista e…").
- Toda fala tem `cena` ou `passo`: algo muda na tela a cada 2 a 4 segundos. Tudo o que a fala cita aparece sendo criado (digitado, fixado, enviado, tocado).
- Cada "Mas tem um problema" vira um `problema`; cada "Pronto! Agora…" vira `resolvido`, `rotulo` ou `comemora`.
- Números só reais ou claramente de exemplo. Nunca invente pesquisa, estatística ou caso.
- Fala em português do Brasil, como o José fala: direto, "você", frases curtas.
- CTA final: "Salva esse vídeo e…" (cena cta salvar) ou "Comenta QUERO que eu te envio o link da Comunidade Nutri+" (cena cta comentar). Nada de e-book nem desconto.

## Mundinho 3D (`"estilo": "mundo"`) — o formato dos hexágonos
Use quando o vídeo é uma sequência de conceitos ou etapas (cada frase termina com "isso é X"). Cada fala com `estacao` cria uma plataforma hexagonal nova no caminho; a câmera vai até ela. **A estação mostra literalmente o que a fala diz** (se fala de outdoor, aparece o outdoor na rua; se fala de jornal, aparece o print da matéria; se fala de anúncio, o print do anúncio patrocinado).

```json
{"titulo": "Isso é marketing!", "estilo": "mundo", "destaques": ["propaganda", "marketing"],
 "falas": [
  {"texto": "Se você coloca uma placa na frente do seu consultório, isso é propaganda.",
   "estacao": {"tipo": "placa", "titulo": "PROPAGANDA", "dados": {"titulo": "Ana Souza", "sub": "Nutricionista · CRN-3 54321"}},
   "passo": [{"rotulo": "PLACA NA FRENTE", "alvo": "placa", "em": "placa"}, {"titulo": true, "em": "propaganda"}]},
  {"texto": "E se tudo isso foi planejado desde o início...", "final": {"titulo": "ISSO É\nMARKETING!", "em": "planejado", "em_titulo": "início"}},
  {"texto": "Isso é marketing!"}
 ]}
```

| tipo de estação | o que aparece | dados | alvos para rotulo |
|---|---|---|---|
| `placa` | consultório por fora com a placa na frente, na rua | titulo, sub, extra, predio | placa, predio |
| `outdoor` | outdoor na rua com carros passando | titulo, sub, botao | painel, rua |
| `anuncio` | celular gigante com o print de um anúncio patrocinado do Instagram + pessoas olhando | usuario, chamada, botao, curtidas, legenda | tela, pessoas |
| `jornal` | celular gigante com o print de uma matéria de portal de notícias (marca fictícia, nunca G1 ou outro veículo real) | portal, editoria, titulo, linha, autor | tela, pessoas |
| `whats` | celular gigante com a conversa do WhatsApp + a nutri | contato, mensagens [{de: "ele"/"eu", msg}] | tela, nutri |
| `agenda` | celular com a agenda da semana | titulo, cheios (0 a 40) | tela |
| `consultorio` | consultório com a nutri e pacientes girando em volta (acompanhamento) | pacientes, coracoes, anel | nutri, predio |
| `pessoas` | um grupo de pessoas | n | pessoas |

- `{"titulo": true, "em": "palavra"}` mostra o título numerado da estação ("1. PROPAGANDA") no topo, quando a palavra é dita.
- `{"rotulo": "TEXTO", "alvo": "tela", "em": "palavra"}` etiqueta presa no objeto 3D (`"cor": "#34a878"` para o ponto verde).
- `final`: a câmera sobe e mostra o caminho inteiro com os títulos; `titulo` (pode ter \n) aparece grande no topo.
- Precisa de uma estação nova para cada conceito; se o vídeo pede algo que não está na tabela, use a estação mais parecida e diga no histórico (ou crie o tipo novo em video/mundo/mundo.js).
