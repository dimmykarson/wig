# Página dedicada WhatsApp

## Contexto

Hoje a UI ([ui/index.html](../../ui/index.html)) exibe os dois canais (WhatsApp e
Instagram) lado a lado, cada um numa coluna de "celular". Para demonstrações e
desenvolvimento focado em WhatsApp, essa tela divide a atenção e limita o tamanho
de cada aparelho.

Esta feature adiciona uma **página nova, dedicada exclusivamente ao WhatsApp**,
servida em `GET /whatsapp`, com dois **modos de visualização selecionáveis**:

- **Modo Celular** — o aparelho WhatsApp em tela cheia, centralizado e maior.
- **Modo WhatsApp Web** — layout desktop com sidebar de conversas à esquerda e
  painel de chat à direita.

O backend (payloads Meta, WebSocket `/ws/whatsapp`, config, callback) **não muda**:
a página nova é puro frontend reutilizando o canal `whatsapp` já existente.

## Motivação técnica — DRY antes da duplicação

Todo o JavaScript da UI atual já é **parametrizado por canal** (`'whatsapp'` /
`'instagram'`): `connectWS`, `sendMsg`, `renderMessage`, mídia, áudio, debug,
config. Criar `whatsapp.html` copiando esse JS duplicaria ~750 linhas idênticas —
violação direta da regra DRY do CLAUDE.md.

Por isso, **antes** de criar a página nova, extraímos o JS e o CSS compartilhados
para arquivos próprios (`ui/shared.js`, `ui/shared.css`), que tanto `index.html`
quanto `whatsapp.html` importam. O `index.html` permanece funcionalmente idêntico.

## Requisitos funcionais

- [ ] RF1: `GET /whatsapp` serve `ui/whatsapp.html` (HTTP 200, `text/html`).
- [ ] RF2: Estáticos (`shared.js`, `shared.css`, e demais assets de `ui/`) são
  servidos pelo backend sem leitura manual de arquivo na rota.
- [ ] RF3: `ui/index.html` continua funcionando exatamente como antes (dois
  celulares, WhatsApp + Instagram), agora importando `shared.css` e `shared.js`.
- [ ] RF4: `ui/whatsapp.html` exibe **somente** o canal WhatsApp, com chat
  totalmente funcional (envio, recebimento, status, mídia, áudio, debug, config)
  via `/ws/whatsapp`.
- [ ] RF5: A página nova tem um **seletor de modo** (Celular / WhatsApp Web) no
  topo. Alternar o modo troca o layout sem recarregar a página nem reconectar o
  WebSocket.
- [ ] RF6: **Modo Celular** — aparelho centralizado, maior que na tela dupla,
  reaproveitando o visual WhatsApp existente.
- [ ] RF7: **Modo WhatsApp Web** — sidebar à esquerda (item de conversa com avatar,
  nome e última mensagem) + painel de chat à direita ocupando a largura restante.
- [ ] RF8: O modo selecionado persiste em `localStorage` e é restaurado no reload.
- [ ] RF9: A config (webhook URL, nome, identificador) e a conversa são as mesmas
  do canal `whatsapp` — a página nova compartilha estado com o canal, não cria um
  estado paralelo. *(Decisão D1 — ver abaixo.)*
- [x] RF10: Layout em duas colunas — emulação à esquerda, painéis (config/debug)
  à direita.
- [x] RF11: Modo WhatsApp Web usa a paleta CLARA real do WhatsApp Web (sidebar
  branca, chat bege com padrão, balão enviado verde-claro, recebido branco).
- [x] RF12: Seletor de **modelo de aparelho** no modo Celular — iPhone 15, Moto G,
  Galaxy S26, Pixel, **iPad** — que muda a moldura (raio dos cantos, espessura/cor
  das bordas e o recorte da câmera: Dynamic Island vs. punch-hole; iPad é mais largo,
  formato tablet). Persistido em `localStorage`.
- [x] RF13: Tema claro (paleta real do WhatsApp) aplicado nos **dois modos**; a
  moldura física do aparelho permanece escura, só a tela fica clara.

## Requisitos não-funcionais

- **Segurança:** sem nova superfície de ataque. As rotas servem arquivos estáticos
  fixos sob `ui/`; nenhum caminho derivado de input do usuário (sem path traversal).
- **Performance:** `shared.js`/`shared.css` viram arquivos estáticos cacheáveis pelo
  browser (hoje o HTML inline é re-baixado inteiro). O seletor de modo é troca de
  classe CSS — sem custo de rede.
- **LGPD:** não se aplica — nenhum dado pessoal novo é coletado, logado ou
  transmitido. A página reusa o canal existente.
- **Zero build:** mantém a premissa do Épico 4.1 — HTML/CSS/JS puros servidos pelo
  FastAPI, sem etapa de build/bundler.

## Breakdown modular

**Fase 1 — Backend (testável com pytest):**
- Montar `StaticFiles` para servir `ui/` em `/static` (ou equivalente).
- Adicionar rota `GET /whatsapp` → `ui/whatsapp.html`.

**Fase 2 — Extração do compartilhado (refactor sem mudança de comportamento):**
- Mover CSS comum de `index.html` para `ui/shared.css`.
- Mover JS comum de `index.html` para `ui/shared.js`.
- `index.html` passa a importar ambos; validar que segue idêntico.

**Fase 3 — Página WhatsApp:**
- Criar `ui/whatsapp.html` com markup só-WhatsApp importando `shared.css`/`shared.js`.
- Implementar seletor de modo + CSS dos dois layouts (Celular / WhatsApp Web).
- Persistir modo em `localStorage`.

## Critérios de aceitação (mapeiam 1:1 para os testes)

- [x] CA1: `GET /whatsapp` retorna 200 e `content-type: text/html`. *(teste pytest)*
- [x] CA2: `GET /` continua retornando 200 e o HTML com os dois canais. *(teste pytest)*
- [x] CA3: O arquivo estático `shared.js` é servido com 200. *(teste pytest)*
- [x] CA4: `whatsapp.html` não contém markup do Instagram e expõe `window.CHANNELS`.
  *(teste pytest + smoke: `grep -c instagram` = 0)*
- [x] CA5: na página nova, alternar Celular ↔ WhatsApp Web troca o layout
  sem reconectar o WS; o modo persiste após reload. *(verificado via Playwright:
  ambos os modos renderizam, toggle ativo correto, modo restaurado do localStorage)*
- [~] CA6 (manual): UI de chat, controles (anexo/mic/enviar) e conexão WS renderizam
  na página nova (dot verde). O round-trip completo de envio/recebimento/status
  depende de um webhook real da app consumidora — validar contra a sua aplicação.
- [x] CA7: o `index.html` (tela dupla) continua 100% funcional após a extração do
  JS/CSS. *(verificado via Playwright: WhatsApp + Instagram lado a lado, ambos os
  WS conectados, config/debug intactos)*

> **Nota sobre TDD:** o projeto não possui harness de teste de frontend (a suíte é
> toda pytest de backend). Os critérios CA1–CA4 são cobertos por testes pytest
> escritos **antes** do código (Red→Green). Os critérios CA5–CA7 são de UI pura sem
> infra de teste automatizada e são verificados manualmente — documentado aqui
> conforme a exceção prevista na Premissa 3 do CLAUDE.md.

## Decisões de arquitetura

- **D1 — Estado compartilhado com o canal:** a página `/whatsapp` usa o **mesmo**
  canal `whatsapp` (mesma config, mesmo WS, mesma conversa) do `index.html`, não um
  canal isolado. Razão: o backend modela estado por canal; criar um canal separado
  exigiria mudança de backend e duplicaria config. Trade-off: abrir as duas páginas
  simultaneamente compartilha a conversa — aceitável para uma ferramenta de dev.
- **D2 — Servir estáticos via `StaticFiles`:** em vez de adicionar mais rotas que
  leem arquivo na mão (como a `/` faz hoje), monta-se `StaticFiles` uma vez. Reduz
  boilerplate e habilita cache do browser para os assets compartilhados.
- **D3 — Seletor de modo por classe CSS:** os dois layouts (Celular / WhatsApp Web)
  coexistem no mesmo `whatsapp.html`; alternar é trocar uma classe no container raiz.
  Evita recarregar a página e reconectar o WebSocket.
- **D4 — Extração antes da nova página:** a refatoração de extrair `shared.js`/
  `shared.css` precede a criação de `whatsapp.html` para nunca duplicar lógica.
