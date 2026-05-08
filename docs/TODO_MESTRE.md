# TODO_MESTRE — mock_rs

> Fonte de verdade do projeto. Toda task deve ser registrada aqui antes de implementada.
> Ao concluir qualquer item: marcar `[x]` imediatamente. Não ao final de um conjunto — tarefa por tarefa.

---

## Contexto e Motivação

Qualquer projeto que integra com WhatsApp ou Instagram via Meta Webhooks precisa, durante o desenvolvimento, simular o comportamento da plataforma real. Hoje, isso exige conta Meta Business, número homologado e infraestrutura de produção — o que cria fricção desnecessária no ciclo de desenvolvimento.

Este projeto é um **mock genérico, configurável e de código aberto** que qualquer time pode rodar localmente (ou em staging) para:

- Simular o envio de mensagens de um contato para sua aplicação
- Receber e visualizar as respostas que sua aplicação envia de volta
- Inspecionar os payloads exatos trafegados em ambos os sentidos
- Desenvolver e testar integrações sem depender de ambiente Meta real

---

## Objetivos

- Simular dois canais de mensageria em uma única interface web: **WhatsApp** e **Instagram**
- Ser **100% configurável pela UI**, sem necessidade de alterar código ou reiniciar o servidor
- Expor a própria **URL de callback** para facilitar a configuração da aplicação consumidora
- Oferecer um **painel de debug** com os payloads completos enviados e recebidos
- Ser distribuível como imagem Docker pública, pronto para uso com uma linha de comando

---

## Não-objetivos

- Não simula autenticação OAuth da Meta
- Não valida tokens de acesso reais
- Não implementa todos os tipos de mensagem da API Meta (escopo inicial: texto)
- Não persiste dados em banco de dados (estado apenas em memória + localStorage)
- Não é adequado para uso em produção — é uma ferramenta de desenvolvimento

---

## Glossário

| Termo | Significado |
|---|---|
| `canal` | Um dos dois simuladores: `whatsapp` ou `instagram` |
| `webhook_url` | URL da aplicação consumidora que recebe os eventos simulados |
| `callback_url` | URL do mock que a aplicação consumidora deve chamar para enviar respostas |
| `identifier` | Número de telefone (WPP) ou `@handle` (Instagram) do contato simulado |
| `wamid` | WhatsApp Message ID — identificador único de mensagem no formato Meta |
| `mid` | Instagram Message ID — equivalente ao `wamid` no Instagram |
| `waba_id` | WhatsApp Business Account ID — identificador da conta business |
| `wa_id` | Identificador do contato no WhatsApp (geralmente `55` + DDD + número) |
| `sender_id` | Identificador do remetente no Instagram |
| payload | Corpo JSON enviado ao webhook da aplicação, no formato Meta oficial |

---

## Arquitetura

### Visão geral

```
┌─────────────────────────────────────────────────────┐
│                    BROWSER (UI)                     │
│                                                     │
│  ┌─────────────────┐    ┌─────────────────────────┐ │
│  │  Celular WPP    │    │    Celular Instagram     │ │
│  │  ┌───────────┐  │    │  ┌─────────────────────┐│ │
│  │  │  Chat UI  │  │    │  │      Chat UI        ││ │
│  │  └─────┬─────┘  │    │  └──────────┬──────────┘│ │
│  │        │ WS     │    │             │ WS         │ │
│  └────────┼────────┘    └─────────────┼────────────┘ │
└───────────┼─────────────────────────-─┼──────────────┘
            │ WebSocket /ws/whatsapp    │ WebSocket /ws/instagram
            ▼                          ▼
┌─────────────────────────────────────────────────────┐
│                   MOCK SERVER                       │
│                                                     │
│  WebSocket Handler ──► Payload Builder ──► HTTP POST│
│       ▲                                      │      │
│       │                                      ▼      │
│  POST /callback/{canal}          webhook_url da app  │
│       ▲                                             │
└───────┼─────────────────────────────────────────────┘
        │ POST /callback/{canal}
┌───────┼─────────────────────────────────────────────┐
│       │       APLICAÇÃO CONSUMIDORA                 │
│  Processa evento ──► chama /callback/{canal}        │
└─────────────────────────────────────────────────────┘
```

### Fluxo: usuário envia mensagem

```
1. Usuário digita mensagem na UI do celular simulado
2. UI envia via WebSocket: {"text": "olá"}
3. Mock monta payload no formato Meta (WPP ou IG)
4. Mock faz POST para webhook_url configurada
5. Mock envia {"type": "sent", "text": "olá", "ts": "14:32"} de volta ao WebSocket
6. UI exibe balão de mensagem enviada
```

### Fluxo: aplicação responde

```
1. Aplicação processa o evento e chama POST /callback/whatsapp (ou /instagram)
2. Mock recebe o JSON de resposta
3. Mock envia {"type": "received", "text": "...", "ts": "14:33"} via WebSocket
4. UI exibe balão de resposta recebida
```

---

## Contrato de API

### Endpoints REST

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check — retorna `{"status": "ok"}` |
| `GET` | `/info` | Retorna URLs de callback do mock e status dos canais |
| `GET` | `/config` | Retorna configuração atual dos dois canais |
| `PATCH` | `/config/{canal}` | Atualiza configuração de um canal sem reiniciar |
| `DELETE` | `/history/{canal}` | Limpa histórico de mensagens do canal |
| `POST` | `/callback/{canal}` | Recebe resposta da aplicação consumidora |
| `WS` | `/ws/{canal}` | WebSocket bidirecional entre UI e backend |

`{canal}` aceita: `whatsapp` ou `instagram`

---

### Schemas

#### `PATCH /config/{canal}` — corpo da requisição

```json
{
  "webhook_url": "https://minha-app.local/api/webhook/",
  "user_name": "João Silva",
  "identifier": "5586999990000"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `webhook_url` | string (URL) | sim | Para onde o mock envia os eventos |
| `user_name` | string | sim | Nome do contato simulado |
| `identifier` | string | sim | Número E.164 (WPP) ou `@handle` (Instagram) |

---

#### `GET /info` — resposta

```json
{
  "base_url": "http://localhost:5504",
  "channels": {
    "whatsapp": {
      "callback_url": "http://localhost:5504/callback/whatsapp",
      "websocket_url": "ws://localhost:5504/ws/whatsapp",
      "configured": true
    },
    "instagram": {
      "callback_url": "http://localhost:5504/callback/instagram",
      "websocket_url": "ws://localhost:5504/ws/instagram",
      "configured": false
    }
  }
}
```

---

#### `POST /callback/{canal}` — corpo esperado da aplicação

```json
{
  "text": "Olá! Como posso ajudar?",
  "type": "text"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `text` | string | sim | Texto da resposta |
| `type` | string | não | Tipo da mensagem (default: `"text"`) |

Resposta de sucesso: `{"ok": true}`

---

### Protocolo WebSocket

**Cliente → Servidor** (UI envia mensagem):

```json
{"text": "mensagem digitada pelo usuário"}
```

**Servidor → Cliente** (eventos enviados à UI):

```json
// mensagem enviada com sucesso ao webhook
{"type": "sent", "text": "olá", "ts": "14:32"}

// aplicação está "digitando" (enviado antes da resposta)
{"type": "typing", "status": true}

// resposta recebida da aplicação
{"type": "received", "msg_type": "text", "text": "Olá!", "ts": "14:33"}

// erro ao chamar o webhook
{"type": "error", "text": "Webhook não respondeu: Connection refused"}

// histórico limpo
{"type": "history_cleared"}
```

---

### Payload WhatsApp (enviado ao webhook da aplicação)

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "MOCK_WABA_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "5586999990000",
          "phone_number_id": "MOCK_PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": {"name": "João Silva"},
          "wa_id": "5586999990000"
        }],
        "messages": [{
          "from": "5586999990000",
          "id": "wamid.mock_a1b2c3d4e5f6g7h8",
          "timestamp": "1746700000",
          "type": "text",
          "text": {"body": "mensagem do usuário"}
        }]
      },
      "field": "messages"
    }]
  }]
}
```

---

### Payload Instagram (enviado ao webhook da aplicação)

```json
{
  "object": "instagram",
  "entry": [{
    "id": "MOCK_IG_ACCOUNT_ID",
    "messaging": [{
      "sender": {"id": "mock_sender_123"},
      "recipient": {"id": "MOCK_IG_PAGE_ID"},
      "timestamp": 1746700000,
      "message": {
        "mid": "mid.mock_a1b2c3d4e5f6g7h8",
        "text": "mensagem do usuário"
      }
    }]
  }]
}
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `5504` | Porta em que o servidor escuta |
| `MOCK_BASE_URL` | `http://localhost:5504` | URL pública do mock — usada para gerar a callback URL exibida na UI |
| `LOG_LEVEL` | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_DEBUG_ENTRIES` | `50` | Máximo de entradas no painel de debug por canal |

---

## Épicos e Tasks

### ÉPICO 0 — Decisões de arquitetura (pré-requisito de tudo)

- [ ] `0.1` Definir stack: Python/FastAPI ou Rust/Axum
- [ ] `0.2` Definir estratégia de persistência de config: apenas memória ou arquivo JSON local (`config.json`)
- [ ] `0.3` Definir estratégia de deploy público: Docker Hub (`dimmy/mock-rs`) ou GitHub Container Registry (`ghcr.io`)
- [ ] `0.4` Definir licença do projeto (sugestão: MIT)

---

### ÉPICO 1 — Infraestrutura e setup

- [ ] `1.1` Inicializar repositório git com `.gitignore` adequado à stack escolhida
- [ ] `1.2` Criar estrutura de pastas do projeto
- [ ] `1.3` Configurar dependências com versões fixas e lockfile
- [ ] `1.4` Configurar linting e formatação (`ruff`+`black` / `clippy`+`rustfmt`)
- [ ] `1.5` Criar `Dockerfile` multi-stage (build + runtime mínimo)
- [ ] `1.6` Criar `docker-compose.yml` standalone para desenvolvimento
- [ ] `1.7` Criar `.env.example` com todas as variáveis documentadas

---

### ÉPICO 2 — Backend: núcleo da aplicação

- [ ] `2.1` Modelar estado dos dois canais em memória
  - `ChannelConfig`: `webhook_url`, `user_name`, `identifier`, `platform`, `configured: bool`
  - `ChannelState`: `connected: bool`, `history: List[Message]`
- [ ] `2.2` Endpoint `GET /health`
- [ ] `2.3` Endpoint `GET /info` — retorna URLs de callback e status de cada canal
- [ ] `2.4` Endpoint `GET /config` — retorna configuração atual dos dois canais
- [ ] `2.5` Endpoint `PATCH /config/{canal}` — atualiza configuração em runtime, valida campos
- [ ] `2.6` Endpoint `DELETE /history/{canal}` — limpa histórico, notifica WebSocket conectado
- [ ] `2.7` Endpoint `POST /callback/{canal}` — recebe resposta da aplicação, roteia ao WebSocket
- [ ] `2.8` WebSocket `/ws/{canal}` — gerencia conexão, reconexão e mensagens bidirecionais
- [ ] `2.9` Configurar CORS para aceitar qualquer origem (ferramenta de dev, sem restrição)
- [ ] `2.10` Logging estruturado com nível configurável via `LOG_LEVEL`

---

### ÉPICO 3 — Backend: payloads Meta

- [ ] `3.1` Gerador de Message ID
  - WhatsApp: `wamid.mock_{16 chars hex}`
  - Instagram: `mid.mock_{16 chars hex}`
- [ ] `3.2` Builder de payload WhatsApp (formato Meta Webhook oficial, campos conforme seção Contrato de API)
- [ ] `3.3` Builder de payload Instagram (formato Meta IG Direct, campos conforme seção Contrato de API)
- [ ] `3.4` Envio assíncrono via HTTP POST para `webhook_url` com timeout de 10s
- [ ] `3.5` Capturar e estruturar erros de entrega: `ConnectionError`, `TimeoutError`, resposta não-2xx
- [ ] `3.6` Emitir evento de debug a cada envio: payload completo + status da resposta HTTP

---

### ÉPICO 4 — Frontend: shell e layout

- [ ] `4.1` HTML/CSS/JS embutido no servidor (sem framework externo, sem bundler — zero dependência de build)
- [ ] `4.2` Layout responsivo: dois frames de celular lado a lado, centralizados na página
- [ ] `4.3` Frame de celular estilo iPhone: notch, status bar, bordas arredondadas
- [ ] `4.4` Cabeçalho de página com nome do projeto e link para repositório GitHub
- [ ] `4.5` Layout em coluna única em telas menores (mobile/tablet) — os frames empilham

---

### ÉPICO 5 — Frontend: chat WhatsApp

- [ ] `5.1` Tema escuro com cor de fundo `#0B141A` e padrão de fundo característico do WPP
- [ ] `5.2` Barra de topo com avatar, nome do contato e status ("online")
- [ ] `5.3` Balão de mensagem enviada (direita, cor `#005C4B`, com cauda)
- [ ] `5.4` Balão de mensagem recebida (esquerda, cor `#202C33`, com cauda)
- [ ] `5.5` Timestamp em cada balão (`HH:MM`)
- [ ] `5.6` Check marks duplos (✓✓) nas mensagens enviadas
- [ ] `5.7` Indicador animado "digitando..." enquanto aguarda resposta
- [ ] `5.8` Campo de texto na barra inferior com botão de envio
- [ ] `5.9` Envio com Enter (Shift+Enter para nova linha) e clique no botão
- [ ] `5.10` Auto-scroll para a última mensagem ao receber ou enviar

---

### ÉPICO 6 — Frontend: chat Instagram

- [ ] `6.1` Tema claro com fundo branco e bordas cinza suave
- [ ] `6.2` Barra de topo com avatar circular com gradiente IG, nome do contato e ícone de câmera
- [ ] `6.3` Balão de mensagem enviada (direita, fundo `#0095F6` — azul Instagram)
- [ ] `6.4` Balão de mensagem recebida (esquerda, fundo `#EFEFEF`)
- [ ] `6.5` Balões sem cauda, bordas muito arredondadas (estilo IG)
- [ ] `6.6` Timestamp ao passar o mouse sobre o balão (tooltip)
- [ ] `6.7` Indicador animado de "digitando..." (três pontos pulsantes)
- [ ] `6.8` Campo de texto com botão de envio e ícone de microfone decorativo
- [ ] `6.9` Auto-scroll para a última mensagem

---

### ÉPICO 7 — Frontend: painel de configuração

- [ ] `7.1` Ícone de engrenagem (⚙) no cabeçalho de cada celular — abre o painel de config
- [ ] `7.2` Painel colapsável (slide down) com os campos:
  - **Webhook URL** — URL para onde o mock envia os eventos (`webhook_url`)
  - **Nome do contato** — nome do remetente simulado (`user_name`)
  - **Identificador** — número E.164 para WPP ou `@handle` para Instagram (`identifier`)
- [ ] `7.3` Botão **"Salvar"** — aplica configuração via `PATCH /config/{canal}` e fecha o painel
- [ ] `7.4` Validação client-side antes de salvar:
  - `webhook_url`: URL válida e não vazia
  - `user_name`: não vazio
  - `identifier`: não vazio; para WPP, apenas dígitos; para IG, começa com `@`
- [ ] `7.5` Caixa de destaque **"URL de Callback"** (somente leitura) com botão **"Copiar"**
  - Exibe: `http://localhost:5504/callback/whatsapp` (ou `/instagram`)
  - Botão muda para "Copiado ✓" por 2s após copiar
- [ ] `7.6` Indicador de status do webhook (ponto verde/vermelho) ao lado da URL — atualizado ao salvar
- [ ] `7.7` Persistência das configurações via `localStorage` — restauradas no reload sem chamar a API
- [ ] `7.8` Botão **"Limpar conversa"** — chama `DELETE /history/{canal}`, limpa UI, mantém config

---

### ÉPICO 8 — Frontend: painel de debug

- [ ] `8.1` Card colapsável abaixo de cada celular: "🔍 Debug — WhatsApp / Instagram"
- [ ] `8.2` Fechado por padrão; estado (aberto/fechado) persistido em `localStorage`
- [ ] `8.3` Cada entrada do log exibe:
  - Direção: `→ ENVIADO` (verde) ou `← RECEBIDO` (azul) ou `✕ ERRO` (vermelho)
  - Timestamp com hora e milissegundos
  - Status HTTP (quando aplicável): `200 OK`, `500 Internal Server Error`, etc.
  - JSON formatado e com syntax highlighting básico (chaves em cor diferente)
- [ ] `8.4` Botão **"Copiar JSON"** em cada entrada — copia o JSON da entrada para o clipboard
- [ ] `8.5` Botão **"Limpar log"** no cabeçalho do card — apaga apenas as entradas do debug
- [ ] `8.6` Limite de `MAX_DEBUG_ENTRIES` entradas (padrão: 50) — entrada mais antiga removida ao atingir o limite
- [ ] `8.7` Scroll interno no card de debug (não expande a página inteira)

---

### ÉPICO 9 — WebSocket: resiliência e reconexão

- [ ] `9.1` Reconexão automática em caso de queda: retry com backoff (1s → 2s → 4s, máx. 30s)
- [ ] `9.2` Indicador visual de conexão WebSocket em cada celular (ponto animado: verde=conectado, cinza=reconectando)
- [ ] `9.3` Fila de mensagens pendentes durante reconexão — reenviar ao reconectar (ou notificar falha)
- [ ] `9.4` Timeout no WebSocket do servidor: fechar conexão inativa após 5 minutos

---

### ÉPICO 10 — Qualidade e testes

- [ ] `10.1` Testes unitários: builder de payload WhatsApp
  - Verificar todos os campos obrigatórios
  - Verificar formato do `wamid` gerado
  - Verificar que o `identifier` do config aparece como `from` e `wa_id`
- [ ] `10.2` Testes unitários: builder de payload Instagram
  - Verificar todos os campos obrigatórios
  - Verificar formato do `mid` gerado
- [ ] `10.3` Testes de integração: `GET /health`, `GET /info`, `GET /config`
- [ ] `10.4` Testes de integração: `PATCH /config/{canal}` — sucesso, campos inválidos, canal inválido
- [ ] `10.5` Testes de integração: `DELETE /history/{canal}`
- [ ] `10.6` Testes de integração: `POST /callback/{canal}` — sucesso, payload malformado, canal inválido
- [ ] `10.7` Testes de integração: envio ao webhook — simular webhook respondendo 200, 500 e timeout
- [ ] `10.8` Cobertura mínima: 80%

---

### ÉPICO 11 — CI/CD e publicação

- [ ] `11.1` GitHub Actions: workflow `test.yml` — executar testes em todo push e pull request
- [ ] `11.2` GitHub Actions: workflow `lint.yml` — linting e formatação em todo push e pull request
- [ ] `11.3` GitHub Actions: workflow `docker-publish.yml` — publicar imagem ao criar tag `v*.*.*`
  - Build multi-platform: `linux/amd64` e `linux/arm64`
  - Push para Docker Hub: `docker.io/{usuario}/mock-rs:latest` e `:{versao}`
- [ ] `11.4` Badges no README: CI status · Docker pulls · Docker image size · License
- [ ] `11.5` Versionamento SemVer: `MAJOR.MINOR.PATCH` — documentado no CONTRIBUTING.md
- [ ] `11.6` `CHANGELOG.md` com formato Keep a Changelog

---

### ÉPICO 12 — Documentação pública

- [ ] `12.1` `README.md` com seções:
  - O que é e para que serve
  - Quickstart com uma linha: `docker run -p 5504:5504 {usuario}/mock-rs`
  - Screenshot da interface
  - Como configurar cada canal (webhook URL, contato, identificador)
  - Como obter a callback URL e configurar na sua aplicação
  - Exemplos de payload enviado (WPP e IG)
  - Formato esperado do callback
  - Todas as variáveis de ambiente com valores padrão
  - docker-compose de exemplo para integrar com outra aplicação
- [ ] `12.2` `CONTRIBUTING.md` — como rodar localmente, como abrir PR, convenção de commits
- [ ] `12.3` `LICENSE` — arquivo de licença (MIT)
- [ ] `12.4` `.github/ISSUE_TEMPLATE/` — templates para bug report e feature request
- [ ] `12.5` `docker-compose.example.yml` — exemplo completo de uso com aplicação consumidora

---

## Ordem de Implementação

```
ÉPICO 0 (decisões)
    └─► ÉPICO 1 (infra)
            └─► ÉPICO 2 (backend core) ──► ÉPICO 10 (testes 2.x)
                    └─► ÉPICO 3 (payloads) ──► ÉPICO 10 (testes 3.x)
                            └─► ÉPICO 4 (frontend shell)
                                    ├─► ÉPICO 5 (chat WPP)
                                    ├─► ÉPICO 6 (chat IG)
                                    ├─► ÉPICO 7 (config)
                                    ├─► ÉPICO 8 (debug)
                                    └─► ÉPICO 9 (WebSocket resiliência)
                                                └─► ÉPICO 11 (CI/CD)
                                                        └─► ÉPICO 12 (docs)
```

Dentro de cada épico: **Red → Green → Refactor**. Escreva o teste antes do código de produção.

---

## Decisões Pendentes

| # | Decisão | Opções | Impacto |
|---|---------|--------|---------|
| D1 | Stack tecnológica | Python 3.12 / FastAPI · Rust / Axum | Define épicos 1, 7, 10 inteiros |
| D2 | Persistência de config | Apenas memória (reset no restart) · `config.json` local | Define `2.1` e UX do `7.7` |
| D3 | Registro Docker | Docker Hub · GitHub Container Registry (ghcr.io) | Define `11.3` |
| D4 | Licença | MIT · Apache 2.0 | Define `12.3` |

---

## Riscos e Dependências

| # | Risco | Mitigação |
|---|-------|-----------|
| R1 | Formato do payload Meta muda sem aviso | Isolar builders em módulo separado; versionar os formatos |
| R2 | Aplicação consumidora não suporta CORS | CORS aberto por padrão em dev; documentar claramente |
| R3 | URL de callback inacessível (NAT, Docker network) | `MOCK_BASE_URL` configurável; documentar uso com ngrok/tunnel |
| R4 | WebSocket cai em proxies com timeout agressivo | Ping/pong keepalive a cada 30s |
