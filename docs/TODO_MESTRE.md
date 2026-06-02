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

- Simular dois canais em uma única página web: **WhatsApp** e **Instagram Direct**
- Ser **100% configurável pela UI** sem reiniciar o servidor
- Gerar payloads **fiéis ao formato oficial Meta** — o que a sua aplicação recebe do mock é idêntico ao que receberia da Meta em produção
- Assinar os payloads com `X-Hub-Signature-256` para que a validação de assinatura da aplicação funcione normalmente
- Expor endpoint de **verificação de webhook** (`GET /webhook/{canal}`) para que a aplicação possa testar seu próprio fluxo de registro
- Simular **status updates** (sent → delivered → read) após o envio de cada mensagem
- Oferecer **painel de debug** com payloads completos em ambos os sentidos
- Ser distribuível como imagem Docker pública — pronto para uso com uma linha de comando

---

## Não-objetivos

- Não simula autenticação OAuth da Meta
- Não valida tokens de acesso reais da Graph API
- Não persiste dados em banco — estado apenas em memória + `localStorage`
- Não é adequado para uso em produção
- **v1:** não suporta mensagens de mídia (imagem, áudio, vídeo, documento, sticker), localização, interativas ou reações — apenas texto. Esses tipos serão adicionados em versões futuras.

---

## Glossário

| Termo | Significado |
|---|---|
| `canal` | Um dos dois simuladores: `whatsapp` ou `instagram` |
| `webhook_url` | URL da aplicação que recebe os eventos simulados |
| `callback_url` | URL do mock que a aplicação chama para enviar respostas |
| `identifier` | Número E.164 (WPP) ou IGSID numérico (Instagram) do contato simulado |
| `wamid` | WhatsApp Message ID — formato: `wamid.HBgL<base64>` |
| `mid` | Instagram Message ID — formato: `mid.$<base64>` |
| `waba_id` | WhatsApp Business Account ID |
| `wa_id` | Identificador E.164 do contato no WhatsApp (ex: `5586999990000`) |
| `IGSID` | Instagram-Scoped User ID — identificador numérico do usuário no Instagram |
| `app_secret` | Chave usada para assinar os payloads com HMAC-SHA256 |
| `verify_token` | Token configurado para o fluxo de verificação de webhook (`hub.verify_token`) |
| `phone_number_id` | ID do número de telefone da conta WPP Business — presente em `metadata` |
| `waba_id` | WhatsApp Business Account ID — aparece como `entry[].id` no payload |
| `ig_account_id` | ID da conta Instagram Business — aparece como `entry[].id` e `recipient.id` |
| `watermark` | Unix timestamp usado nos read/delivery receipts do Instagram como marca d'água |
| `context` | Campo opcional no payload WPP indicando a qual mensagem anterior o usuário está respondendo |

---

## Arquitetura

### Visão geral

```
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER (UI)                         │
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────────┐   │
│  │    Celular WPP       │    │    Celular Instagram      │   │
│  │  ┌────────────────┐  │    │  ┌──────────────────────┐│   │
│  │  │    Chat UI     │  │    │  │      Chat UI         ││   │
│  │  └───────┬────────┘  │    │  └──────────┬───────────┘│   │
│  │          │ WS        │    │             │ WS          │   │
│  └──────────┼───────────┘    └─────────────┼────────────┘   │
└─────────────┼─────────────────────────────-┼────────────────┘
              │ /ws/whatsapp                 │ /ws/instagram
              ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       MOCK SERVER                           │
│                                                             │
│  WS Handler → Payload Builder → X-Hub-Signature → HTTP POST │
│      ▲                                              │       │
│      │                                              ▼       │
│  POST /callback/{canal}                    webhook_url      │
│      ▲                                                      │
│  GET /webhook/{canal}  ← verificação de webhook da app      │
└──────┼──────────────────────────────────────────────────────┘
       │ POST /callback/{canal}
┌──────┼──────────────────────────────────────────────────────┐
│      │             APLICAÇÃO CONSUMIDORA                    │
│  Valida X-Hub-Signature → processa → chama /callback        │
└─────────────────────────────────────────────────────────────┘
```

### Fluxo: usuário envia mensagem

```
1. Usuário digita mensagem na UI
2. UI envia via WebSocket: {"text": "olá"}
3. Mock gera message ID único (wamid / mid)
4. Mock monta payload no formato Meta oficial
5. Mock calcula X-Hub-Signature-256 com HMAC-SHA256(app_secret, body)
6. Mock faz POST para webhook_url com o header de assinatura
7. Mock envia {"type": "sent", "text": "olá", "ts": "14:32"} ao WebSocket
8. Após 1s: mock dispara status "delivered" (simulação)
9. Após 3s: mock dispara status "read" (simulação)
```

### Fluxo: aplicação responde

```
1. Aplicação processa o evento e chama POST /callback/whatsapp (ou /instagram)
2. Mock recebe o JSON de resposta
3. Mock envia {"type": "received", "text": "...", "ts": "14:33"} via WebSocket
4. UI exibe balão de resposta
```

### Fluxo: verificação de webhook

```
1. Desenvolvedor acessa GET /webhook/whatsapp?hub.mode=subscribe
                                              &hub.verify_token=<token>
                                              &hub.challenge=<random>
2. Mock valida hub.verify_token contra VERIFY_TOKEN configurado
3. Mock responde com hub.challenge em texto puro (HTTP 200)
   ou HTTP 403 se o token não bater
```

---

## Contrato de API

### Endpoints REST

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check — `{"status": "ok"}` |
| `GET` | `/info` | URLs de callback e status dos canais |
| `GET` | `/config` | Configuração atual dos dois canais |
| `PATCH` | `/config/{canal}` | Atualiza configuração em runtime |
| `DELETE` | `/history/{canal}` | Limpa histórico de mensagens |
| `GET` | `/webhook/{canal}` | Fluxo de verificação de webhook (`hub.challenge`) |
| `POST` | `/callback/{canal}` | Recebe resposta da aplicação |
| `WS` | `/ws/{canal}` | WebSocket bidirecional UI ↔ backend |

`{canal}`: `whatsapp` ou `instagram`

---

### `PATCH /config/{canal}` — corpo

```json
{
  "webhook_url": "https://minha-app.local/api/webhook/",
  "user_name": "João Silva",
  "identifier": "5586999990000"
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `webhook_url` | string (URL) | Para onde o mock envia os eventos |
| `user_name` | string | Nome do contato simulado |
| `identifier` | string | Número E.164 (WPP) ou IGSID numérico (Instagram) |

---

### `GET /webhook/{canal}` — verificação de webhook

Simula o fluxo de verificação que a Meta faz ao registrar um webhook.

**Query params recebidos:**

| Param | Valor esperado |
|---|---|
| `hub.mode` | `subscribe` |
| `hub.verify_token` | Deve bater com `VERIFY_TOKEN` configurado no mock |
| `hub.challenge` | String aleatória — devolvida integralmente na resposta |

**Resposta de sucesso:** `200 text/plain` com o valor de `hub.challenge`
**Resposta de falha:** `403 Forbidden`

---

### `GET /info` — resposta

```json
{
  "base_url": "http://localhost:5504",
  "channels": {
    "whatsapp": {
      "callback_url": "http://localhost:5504/callback/whatsapp",
      "webhook_verification_url": "http://localhost:5504/webhook/whatsapp",
      "websocket_url": "ws://localhost:5504/ws/whatsapp",
      "configured": true
    },
    "instagram": {
      "callback_url": "http://localhost:5504/callback/instagram",
      "webhook_verification_url": "http://localhost:5504/webhook/instagram",
      "websocket_url": "ws://localhost:5504/ws/instagram",
      "configured": false
    }
  }
}
```

---

### `POST /callback/{canal}` — formato esperado da aplicação

```json
{
  "text": "Olá! Como posso ajudar?",
  "type": "text"
}
```

Resposta: `200 {"ok": true}`

---

### Protocolo WebSocket

**Cliente → Servidor:**
```json
{"text": "mensagem do usuário"}
```

**Servidor → Cliente:**
```json
{"type": "sent",     "text": "olá",    "ts": "14:32"}
{"type": "typing",   "status": true}
{"type": "received", "msg_type": "text", "text": "Olá!", "ts": "14:33"}
{"type": "status",   "status": "delivered", "ts": "14:32"}
{"type": "status",   "status": "read",      "ts": "14:32"}
{"type": "error",    "text": "Webhook não respondeu: Connection refused"}
{"type": "history_cleared"}
```

---

### Payload WhatsApp — enviado ao webhook da aplicação

O payload é **idêntico ao que a Meta envia em produção**, incluindo o header `X-Hub-Signature-256`.

**Header:**
```
X-Hub-Signature-256: sha256=<HMAC-SHA256(app_secret, raw_body)>
```

**Corpo (texto):**
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
          "profile": { "name": "João Silva" },
          "wa_id": "5586999990000"
        }],
        "messages": [{
          "from": "5586999990000",
          "id": "wamid.HBgLmock<16-hex-chars>",
          "timestamp": "1746700000",
          "type": "text",
          "text": { "body": "mensagem do usuário" }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

**Status update (simulado após envio) — `field` é sempre `"messages"`, mesmo para status:**
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
        "statuses": [{
          "id": "wamid.HBgLmock<16-hex-chars>",
          "recipient_id": "5586999990000",
          "status": "delivered",
          "timestamp": "1746700001",
          "conversation": {
            "id": "MOCK_CONV_ID",
            "origin": { "type": "service" }
          },
          "pricing": {
            "billable": false,
            "pricing_model": "CBP",
            "category": "service"
          }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

---

### Payload Instagram — enviado ao webhook da aplicação

**Estrutura diferente do WhatsApp:** usa `messaging` direto no entry, sem camada `changes`.

**Header:**
```
X-Hub-Signature-256: sha256=<HMAC-SHA256(app_secret, raw_body)>
```

**Corpo (texto):**
```json
{
  "object": "instagram",
  "entry": [{
    "id": "MOCK_IG_ACCOUNT_ID",
    "time": 1746700000,
    "messaging": [{
      "sender":    { "id": "123456789" },
      "recipient": { "id": "MOCK_IG_ACCOUNT_ID" },
      "timestamp": 1746700000,
      "message": {
        "mid": "mid.$mock<16-hex-chars>",
        "text": "mensagem do usuário",
        "attachments": [],
        "is_deleted": false,
        "is_echo": false,
        "is_unsupported": false
      }
    }]
  }]
}
```

**Delivery receipt (simulado ~1s após envio):**
```json
{
  "object": "instagram",
  "entry": [{
    "id": "MOCK_IG_ACCOUNT_ID",
    "time": 1746700001,
    "messaging": [{
      "sender":    { "id": "123456789" },
      "recipient": { "id": "MOCK_IG_ACCOUNT_ID" },
      "timestamp": 1746700001,
      "delivery": {
        "mids": ["mid.$mock<16-hex-chars>"],
        "watermark": 1746700000
      }
    }]
  }]
}
```

**Read receipt (simulado ~3s após envio):**
```json
{
  "object": "instagram",
  "entry": [{
    "id": "MOCK_IG_ACCOUNT_ID",
    "time": 1746700003,
    "messaging": [{
      "sender":    { "id": "123456789" },
      "recipient": { "id": "MOCK_IG_ACCOUNT_ID" },
      "timestamp": 1746700003,
      "read": { "watermark": 1746700000 }
    }]
  }]
}
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `5504` | Porta do servidor |
| `MOCK_BASE_URL` | `http://localhost:5504` | URL pública do mock — usada para gerar callback URLs na UI |
| `APP_SECRET` | `mock-secret` | Chave para assinar os payloads com `X-Hub-Signature-256` |
| `VERIFY_TOKEN` | `mock-verify-token` | Token para o fluxo de verificação de webhook (`hub.verify_token`) |
| `LOG_LEVEL` | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_DEBUG_ENTRIES` | `50` | Máximo de entradas no painel de debug por canal |
| `STATUS_DELIVERED_DELAY_MS` | `1000` | Delay para disparar status "delivered" após envio (WPP) |
| `STATUS_READ_DELAY_MS` | `3000` | Delay para disparar status "read" após envio (WPP) |

---

## Épicos e Tasks

### ÉPICO 0 — Decisões de arquitetura (pré-requisito de tudo)

- [x] `0.1` Definir stack: **Python 3.12 / FastAPI** ✓
- [x] `0.2` Definir persistência de config: **`config.json` local** ✓
- [x] `0.3` Definir registro Docker: **Docker Hub** ✓
- [x] `0.4` Definir licença: **MIT** ✓
- [x] `0.5` Definir escopo de tipos de mensagem: **v1 = somente texto**; v2 = mídia + caption, localização, interativas, reações ✓
  - Quando a UI enviar mídia futuramente, o payload deve incluir campo `caption` opcional junto ao objeto de mídia

---

### ÉPICO 1 — Infraestrutura e setup

- [x] `1.1` Inicializar estrutura de pastas e dependências com lockfile
- [x] `1.2` Configurar linting e formatação (`ruff` + `black`)
- [x] `1.3` `Dockerfile` multi-stage (build + runtime mínimo)
- [x] `1.4` `docker-compose.yml` standalone para desenvolvimento
- [x] `1.5` `.env.example` com todas as variáveis documentadas

---

### ÉPICO 2 — Backend: núcleo da aplicação

- [x] `2.1` Modelar estado dos dois canais em memória
  - `ChannelConfig`: `webhook_url`, `user_name`, `identifier`, `platform`, `configured: bool`
    - WPP: inclui `waba_id` e `phone_number_id` (gerados como mock fixo, mas configuráveis)
    - Instagram: inclui `ig_account_id` e `ig_page_id` (gerados como mock fixo, mas configuráveis)
  - `ChannelState`: `ws_connected: bool`, `history: List[Message]`
- [x] `2.2` `GET /health`
- [x] `2.3` `GET /info` — URLs de callback, verificação e WebSocket por canal
- [x] `2.4` `GET /config` — configuração atual dos dois canais
- [x] `2.5` `PATCH /config/{canal}` — valida e aplica nova configuração em runtime
- [x] `2.6` `DELETE /history/{canal}` — limpa histórico, notifica WebSocket
- [x] `2.7` `GET /webhook/{canal}` — fluxo de verificação: valida `hub.verify_token`, responde com `hub.challenge`
- [x] `2.8` `POST /callback/{canal}` — recebe resposta da aplicação, roteia ao WebSocket correto
- [x] `2.9` `WS /ws/{canal}` — gerencia conexão, desconexão e mensagens bidirecionais
- [x] `2.10` Configurar CORS aberto (ferramenta de dev)
- [x] `2.11` Logging estruturado com nível configurável via `LOG_LEVEL`

---

### ÉPICO 3 — Backend: payloads Meta fiéis

- [x] `3.1` Gerador de Message ID (`wamid.HBgL<hex16>` e `mid.$mock<hex16>`)
- [x] `3.2` Builder de payload WhatsApp — texto (todos os campos conforme spec)
- [x] `3.3` Builder de payload WhatsApp — status update com `field: "messages"`, `conversation` e `pricing`
- [x] `3.4` Builder de payload Instagram — texto (estrutura `messaging` conforme spec)
- [x] `3.5` Builder de payload Instagram — delivery receipt (`delivery.mids` + `watermark`)
- [x] `3.6` Builder de payload Instagram — read receipt (`read.watermark`)
- [x] `3.7` Assinatura `X-Hub-Signature-256` via HMAC-SHA256
- [x] `3.8` Envio assíncrono via HTTP POST com header de assinatura e timeout de 10s
- [x] `3.9` Tratamento de erros: `ConnectionError`, `TimeoutError`, resposta não-2xx
- [x] `3.10` Simulação de status/receipts com delay configurável (WPP e Instagram)
- [x] `3.11` Entradas de debug a cada envio, status e erro
- [x] `3.12` Callback responde 200 imediatamente antes de processar

---

### ÉPICO 4 — Frontend: shell e layout

- [x] `4.1` HTML/CSS/JS em `ui/index.html`, servido pelo FastAPI — zero dependência de build
- [x] `4.2` Dois frames de celular lado a lado, centralizados na viewport
- [x] `4.3` Frame estilo iPhone: notch, status bar, bordas arredondadas
- [x] `4.4` Cabeçalho de página com nome do projeto e link para repositório
- [x] `4.5` Em telas menores: frames empilham em coluna única

---

### ÉPICO 5 — Frontend: chat WhatsApp

- [x] `5.1` Tema escuro — fundo `#0B141A`, padrão de fundo característico do WPP
- [x] `5.2` Barra de topo: avatar, nome do contato, status "online"
- [x] `5.3` Balão enviado (direita, `#005C4B`, com cauda)
- [x] `5.4` Balão recebido (esquerda, `#202C33`, com cauda)
- [x] `5.5` Timestamp em cada balão
- [x] `5.6` Check marks: ✓ enviado · ✓✓ entregue · ✓✓ azul lido (atualiza via evento `status`)
- [x] `5.7` Indicador "digitando..." animado enquanto aguarda resposta
- [x] `5.8` Campo de texto + botão enviar; Enter envia, Shift+Enter quebra linha
- [x] `5.9` Auto-scroll para última mensagem

---

### ÉPICO 6 — Frontend: chat Instagram

- [x] `6.1` Tema claro — fundo branco, bordas cinza suave
- [x] `6.2` Barra de topo: avatar com gradiente IG, nome do contato
- [x] `6.3` Balão enviado (direita, `#0095F6`)
- [x] `6.4` Balão recebido (esquerda, `#EFEFEF`)
- [x] `6.5` Balões sem cauda, bordas muito arredondadas
- [x] `6.6` Timestamp como tooltip ao passar o mouse
- [x] `6.7` Indicador "digitando..." (três pontos pulsantes)
- [x] `6.8` Campo de texto + botão enviar
- [x] `6.9` Auto-scroll para última mensagem

---

### ÉPICO 7 — Frontend: painel de configuração

- [x] `7.1` Ícone ⚙ no cabeçalho de cada celular — abre painel colapsável
- [x] `7.2` Campos: Webhook URL · Nome do contato · Identificador
- [x] `7.3` Botão "Salvar" — `PATCH /config/{canal}` + fecha painel
- [x] `7.4` Validação client-side: URL válida, campos não vazios, formato do identificador
- [x] `7.5` Caixa "URL de Callback" (read-only + botão Copiar com feedback "Copiado ✓")
- [x] `7.6` Caixa "URL de Verificação" (read-only + botão Copiar)
- [x] `7.7` Caixa "Verify Token" (read-only + botão Copiar)
- [x] `7.8` Caixa "App Secret" (read-only + botão Copiar)
- [x] `7.9` Indicador verde/vermelho de status do webhook — atualizado ao salvar
- [x] `7.10` Persistência via `localStorage` — restaura configuração no reload
- [x] `7.11` Botão "Limpar conversa" — `DELETE /history/{canal}`, limpa UI, mantém config

---

### ÉPICO 8 — Frontend: painel de debug

- [x] `8.1` Card colapsável abaixo de cada celular: "🔍 Debug"
- [x] `8.2` Fechado por padrão; estado persistido em `localStorage`
- [x] `8.3` Cada entrada: direção colorida · timestamp com ms · status HTTP · JSON com syntax highlighting
- [x] `8.4` Botão "Copiar JSON" por entrada
- [x] `8.5` Botão "Limpar log"
- [x] `8.6` Limite de `MAX_DEBUG_ENTRIES` entradas (FIFO)
- [x] `8.7` Scroll interno no card

---

### ÉPICO 9 — WebSocket: resiliência

- [x] `9.1` Reconexão automática com backoff exponencial: 1s → 2s → 4s → ... → 30s
- [x] `9.2` Indicador visual de conexão: ponto verde (conectado) / laranja pulsante (reconectando)
- [x] `9.3` Ping/keepalive a cada 25s para manter conexão viva em proxies
- [x] `9.4` Timeout no servidor: fechar conexão inativa após 5 min

---

### ÉPICO 10 — Qualidade e testes

- [x] `10.1` Testes unitários: gerador de Message ID (formato wamid e mid)
- [x] `10.2` Testes unitários: builder payload WPP texto — todos os campos obrigatórios
- [x] `10.3` Testes unitários: builder payload WPP status update
  - Verificar que `field` é `"messages"` (não `"message_status"`)
  - Verificar presença dos campos `conversation` e `pricing`
- [x] `10.4` Testes unitários: builder payload Instagram texto — estrutura `messaging`
- [x] `10.5` Testes unitários: builder payload Instagram delivery receipt (`delivery.mids` + `watermark`)
- [x] `10.5b` Testes unitários: builder payload Instagram read receipt (`read.watermark`)
- [x] `10.6` Testes unitários: geração de `X-Hub-Signature-256`
- [x] `10.7` Testes unitários: fluxo de verificação `GET /webhook/{canal}`
  - Token correto → 200 + challenge
  - Token errado → 403
  - `hub.mode` diferente de `subscribe` → 403
- [x] `10.8` Testes de integração: `PATCH /config/{canal}` — sucesso, campos inválidos, canal inválido
- [x] `10.9` Testes de integração: `DELETE /history/{canal}`
- [x] `10.10` Testes de integração: `POST /callback/{canal}` — sucesso, payload malformado, canal inválido
- [x] `10.11` Testes de integração: envio ao webhook — simular 200, 500 e timeout
- [x] `10.12` Cobertura mínima: 80% (98% atingida, 68 testes)

---

### ÉPICO 11 — CI/CD e publicação

- [x] `11.1` GitHub Actions `test.yml` — testes em todo push e PR
- [x] `11.2` GitHub Actions `lint.yml` — linting e formatação em todo push e PR
- [x] `11.3` GitHub Actions `docker-publish.yml` — publicar imagem ao criar tag `v*.*.*`
  - Build multi-platform: `linux/amd64` e `linux/arm64`
  - Push para registro escolhido em D3
- [x] `11.4` Badges no README: CI · lint · Docker pulls · image size · license
- [x] `11.5` `CHANGELOG.md` com formato Keep a Changelog

---

### ÉPICO 12 — Documentação pública

- [x] `12.1` `README.md` completo (ver seção separada no repositório)
- [x] `12.2` `CONTRIBUTING.md` — como rodar localmente, abrir PR, convenção de commits
- [x] `12.3` `LICENSE` (MIT)
- [x] `12.4` `.github/ISSUE_TEMPLATE/` — bug report e feature request
- [x] `12.5` `docker-compose.example.yml` — exemplo de uso com aplicação consumidora

---

### ÉPICO 13 — Página dedicada WhatsApp → [spec](specs/pagina-whatsapp.md)

> Página nova em `GET /whatsapp`, só WhatsApp, com dois modos selecionáveis
> (Celular em tela cheia · WhatsApp Web desktop). Reutiliza o canal `whatsapp`
> existente — backend de payloads/WS/config inalterado. Extração de JS/CSS
> compartilhados antes de criar a página (DRY).

**Fase 1 — Backend (TDD pytest):**
- [x] `13.1` Teste de integração: `GET /whatsapp` → 200 `text/html` (Red→Green)
- [x] `13.2` Teste de integração: `GET /` continua 200 com os dois canais
- [x] `13.3` Teste de integração: estático `shared.js` servido com 200
- [x] `13.4` Montar `StaticFiles` para `ui/` e adicionar rota `GET /whatsapp`

**Fase 2 — Extração compartilhada (refactor sem mudança de comportamento):**
- [x] `13.5` Extrair CSS comum de `index.html` → `ui/shared.css`
- [x] `13.6` Extrair JS comum de `index.html` → `ui/shared.js`
- [x] `13.7` `index.html` importa `shared.css`/`shared.js`; CHANNELS parametriza boot

**Fase 3 — Página WhatsApp:**
- [x] `13.8` `ui/whatsapp.html` — markup só-WhatsApp importando shared
- [x] `13.9` Seletor de modo (Celular / WhatsApp Web) + persistência em `localStorage`
- [x] `13.10` CSS do Modo Celular (aparelho centralizado, maior)
- [x] `13.11` CSS do Modo WhatsApp Web (sidebar de conversas + painel de chat)
- [x] `13.12` Verificação visual (Playwright): dois modos renderizam + paridade do index.html ✓ — round-trip de mensagem real fica para validação contra a app consumidora

**Fase 4 — Refinamentos visuais:**
- [x] `13.13` Layout em duas colunas (emulação à esquerda, painéis à direita)
- [x] `13.14` Paleta clara real do WhatsApp Web no modo web
- [x] `13.15` Seletor de modelo de aparelho (iPhone 15 · Moto G · Galaxy S26 · Pixel · iPad) com moldura/recorte de câmera próprios, persistido em `localStorage`
- [x] `13.16` Tema claro aplicado nos dois modos (Celular e Web); moldura do device permanece escura
- [x] `13.17` fix: renderizar marcação WhatsApp no balão (`*negrito*`, `_itálico_`, `~tachado~`, ```` ```mono``` ````) e preservar quebras de linha `\n` — antes mostrava asteriscos crus e colava a lista numa linha só (afeta index.html e whatsapp.html via shared.js)

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
                                    ├─► ÉPICO 7 (config)     ──► ÉPICO 10 (testes 7.x)
                                    ├─► ÉPICO 8 (debug)
                                    └─► ÉPICO 9 (WS resiliência)
                                                └─► ÉPICO 11 (CI/CD)
                                                        └─► ÉPICO 12 (docs)
```

Dentro de cada épico: **Red → Green → Refactor** — escreva o teste antes do código de produção.

---

## Decisões Pendentes

| # | Decisão | Opções | Impacto |
|---|---------|--------|---------|
| D1 | Stack | Python 3.12 / FastAPI · Rust / Axum | Define épicos 1, 10 inteiros |
| D2 | Persistência de config | **`config.json` local** ✓ | Define `2.1` e UX do `7.10` |
| D3 | Registro Docker | **Docker Hub** ✓ | Define `11.3` |
| D4 | Licença | **MIT** ✓ | Define `12.3` |
| D5 | Tipos de mensagem v1 | Somente texto *(confirmado)* · incluir imagem | Define `3.2`, `3.4`, Épicos 5 e 6 |

---

## Riscos e Dependências

| # | Risco | Mitigação |
|---|-------|-----------|
| R1 | Formato do payload Meta muda sem aviso | Builders isolados em módulo próprio; versionar os formatos no README |
| R2 | Aplicação não aceita requests sem CORS | CORS aberto por padrão; documentar claramente |
| R3 | Callback URL inacessível por NAT ou Docker network | `MOCK_BASE_URL` configurável; documentar uso com ngrok |
| R4 | WebSocket cai em proxies com timeout agressivo | Ping/pong keepalive a cada 30s (Épico 9.3) |
| R5 | Aplicação rejeita payload por `X-Hub-Signature-256` inválida | `APP_SECRET` configurável; documentar como alinhar com a app |
| R6 | App valida `field` no payload de status — mock usava valor errado | Corrigido: `field` agora é `"messages"` em todos os casos (spec oficial) |
