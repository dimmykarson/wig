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

- [ ] `0.1` Definir stack: Python 3.12 / FastAPI ou Rust / Axum
- [ ] `0.2` Definir persistência de config: apenas memória ou arquivo `config.json` local
- [ ] `0.3` Definir registro Docker: Docker Hub ou GitHub Container Registry (ghcr.io)
- [ ] `0.4` Definir licença: MIT ou Apache 2.0
- [ ] `0.5` Definir escopo de tipos de mensagem para v1 (confirmado: somente texto) e roadmap de v2 (mídia, localização, interativas, reações)

---

### ÉPICO 1 — Infraestrutura e setup

- [ ] `1.1` Inicializar estrutura de pastas e dependências com lockfile
- [ ] `1.2` Configurar linting e formatação (`ruff`+`black` / `clippy`+`rustfmt`)
- [ ] `1.3` `Dockerfile` multi-stage (build + runtime mínimo)
- [ ] `1.4` `docker-compose.yml` standalone para desenvolvimento
- [ ] `1.5` `.env.example` com todas as variáveis documentadas

---

### ÉPICO 2 — Backend: núcleo da aplicação

- [ ] `2.1` Modelar estado dos dois canais em memória
  - `ChannelConfig`: `webhook_url`, `user_name`, `identifier`, `platform`, `configured: bool`
    - WPP: inclui `waba_id` e `phone_number_id` (gerados como mock fixo, mas configuráveis)
    - Instagram: inclui `ig_account_id` e `ig_page_id` (gerados como mock fixo, mas configuráveis)
  - `ChannelState`: `ws_connected: bool`, `history: List[Message]`
- [ ] `2.2` `GET /health`
- [ ] `2.3` `GET /info` — URLs de callback, verificação e WebSocket por canal
- [ ] `2.4` `GET /config` — configuração atual dos dois canais
- [ ] `2.5` `PATCH /config/{canal}` — valida e aplica nova configuração em runtime
- [ ] `2.6` `DELETE /history/{canal}` — limpa histórico, notifica WebSocket
- [ ] `2.7` `GET /webhook/{canal}` — fluxo de verificação: valida `hub.verify_token`, responde com `hub.challenge`
- [ ] `2.8` `POST /callback/{canal}` — recebe resposta da aplicação, roteia ao WebSocket correto
- [ ] `2.9` `WS /ws/{canal}` — gerencia conexão, desconexão e mensagens bidirecionais
- [ ] `2.10` Configurar CORS aberto (ferramenta de dev)
- [ ] `2.11` Logging estruturado com nível configurável via `LOG_LEVEL`

---

### ÉPICO 3 — Backend: payloads Meta fiéis

- [ ] `3.1` Gerador de Message ID
  - WhatsApp: `wamid.HBgL<uuid4().hex[:16]>`
  - Instagram: `mid.$<uuid4().hex[:16]>`
- [ ] `3.2` Builder de payload WhatsApp — texto (todos os campos conforme spec)
  - Campo `context` opcional: `{"from": "<wa_id>", "id": "<wamid>"}` para replies
- [ ] `3.3` Builder de payload WhatsApp — status update (`delivered`, `read`)
  - `field` deve ser `"messages"` (não `"message_status"`) — conforme spec oficial
  - Incluir campos `conversation` e `pricing` no objeto de status
- [ ] `3.4` Builder de payload Instagram — texto (estrutura `messaging` conforme spec)
- [ ] `3.5` Builder de payload Instagram — delivery receipt (`messaging.delivery.mids` + `watermark`)
- [ ] `3.6` Builder de payload Instagram — read receipt (`messaging.read.watermark`)
- [ ] `3.7` Assinatura `X-Hub-Signature-256`: `sha256=HMAC-SHA256(APP_SECRET, raw_body)`
- [ ] `3.8` Envio assíncrono via HTTP POST com header de assinatura e timeout de 10s
- [ ] `3.9` Tratamento de erros: `ConnectionError`, `TimeoutError`, resposta não-2xx
- [ ] `3.10` Simulação de status/receipts com delay configurável:
  - WPP: `delivered` após `STATUS_DELIVERED_DELAY_MS`, `read` após `STATUS_READ_DELAY_MS`
  - Instagram: `delivery` após `STATUS_DELIVERED_DELAY_MS`, `read` após `STATUS_READ_DELAY_MS`
- [ ] `3.11` Emitir entrada de debug a cada envio, status e erro
- [ ] `3.12` Responder ao callback com `200 OK` imediatamente antes de processar (evitar timeout da app)

---

### ÉPICO 4 — Frontend: shell e layout

- [ ] `4.1` HTML/CSS/JS embutido no servidor — zero dependência de build externo
- [ ] `4.2` Dois frames de celular lado a lado, centralizados na viewport
- [ ] `4.3` Frame estilo iPhone: notch, status bar, bordas arredondadas
- [ ] `4.4` Cabeçalho de página com nome do projeto e link para repositório
- [ ] `4.5` Em telas menores: frames empilham em coluna única

---

### ÉPICO 5 — Frontend: chat WhatsApp

- [ ] `5.1` Tema escuro — fundo `#0B141A`, padrão de fundo característico do WPP
- [ ] `5.2` Barra de topo: avatar, nome do contato, status "online"
- [ ] `5.3` Balão enviado (direita, `#005C4B`, com cauda)
- [ ] `5.4` Balão recebido (esquerda, `#202C33`, com cauda)
- [ ] `5.5` Timestamp em cada balão
- [ ] `5.6` Check marks: ✓ enviado · ✓✓ entregue · ✓✓ azul lido (atualiza via evento `status`)
- [ ] `5.7` Indicador "digitando..." animado enquanto aguarda resposta
- [ ] `5.8` Campo de texto + botão enviar; Enter envia, Shift+Enter quebra linha
- [ ] `5.9` Auto-scroll para última mensagem

---

### ÉPICO 6 — Frontend: chat Instagram

- [ ] `6.1` Tema claro — fundo branco, bordas cinza suave
- [ ] `6.2` Barra de topo: avatar com gradiente IG, nome do contato
- [ ] `6.3` Balão enviado (direita, `#0095F6`)
- [ ] `6.4` Balão recebido (esquerda, `#EFEFEF`)
- [ ] `6.5` Balões sem cauda, bordas muito arredondadas
- [ ] `6.6` Timestamp como tooltip ao passar o mouse
- [ ] `6.7` Indicador "digitando..." (três pontos pulsantes)
- [ ] `6.8` Campo de texto + botão enviar
- [ ] `6.9` Auto-scroll para última mensagem

---

### ÉPICO 7 — Frontend: painel de configuração

- [ ] `7.1` Ícone ⚙ no cabeçalho de cada celular — abre painel colapsável
- [ ] `7.2` Campos do painel:
  - **Webhook URL** — onde o mock envia os eventos
  - **Nome do contato** — remetente simulado
  - **Identificador** — número E.164 (WPP) ou IGSID (Instagram)
- [ ] `7.3` Botão "Salvar" — `PATCH /config/{canal}` + fecha painel
- [ ] `7.4` Validação client-side: URL válida, campos não vazios, formato do identificador
- [ ] `7.5` Caixa "URL de Callback" (read-only + botão Copiar com feedback "Copiado ✓")
- [ ] `7.6` Caixa "URL de Verificação" (read-only + botão Copiar) — para registrar no painel Meta
- [ ] `7.7` Caixa "Verify Token" (read-only + botão Copiar) — valor de `VERIFY_TOKEN` que a app deve esperar
- [ ] `7.8` Caixa "App Secret" (read-only + botão Copiar) — valor de `APP_SECRET` para configurar validação de assinatura na app
- [ ] `7.9` Indicador verde/vermelho de status do webhook — atualizado ao salvar
- [ ] `7.10` Persistência via `localStorage` — restaura configuração no reload
- [ ] `7.11` Botão "Limpar conversa" — `DELETE /history/{canal}`, limpa UI, mantém config

---

### ÉPICO 8 — Frontend: painel de debug

- [ ] `8.1` Card colapsável abaixo de cada celular: "🔍 Debug"
- [ ] `8.2` Fechado por padrão; estado persistido em `localStorage`
- [ ] `8.3` Cada entrada exibe:
  - Direção: `→ ENVIADO` (verde) · `← RECEBIDO` (azul) · `⚡ STATUS` (cinza) · `✕ ERRO` (vermelho)
  - Timestamp com hora e milissegundos
  - Status HTTP quando aplicável
  - JSON formatado com syntax highlighting básico
- [ ] `8.4` Botão "Copiar JSON" por entrada
- [ ] `8.5` Botão "Limpar log" — apaga só as entradas de debug
- [ ] `8.6` Limite de `MAX_DEBUG_ENTRIES` entradas; remove a mais antiga ao atingir o limite
- [ ] `8.7` Scroll interno no card — não expande a página

---

### ÉPICO 9 — WebSocket: resiliência

- [ ] `9.1` Reconexão automática com backoff exponencial: 1s → 2s → 4s → 8s (máx. 30s)
- [ ] `9.2` Indicador visual de conexão por celular: ponto verde (conectado) / cinza pulsante (reconectando)
- [ ] `9.3` Ping/pong keepalive a cada 30s para manter conexão viva em proxies
- [ ] `9.4` Timeout no servidor: fechar conexão inativa após 5 min

---

### ÉPICO 10 — Qualidade e testes

- [ ] `10.1` Testes unitários: gerador de Message ID (formato wamid e mid)
- [ ] `10.2` Testes unitários: builder payload WPP texto — todos os campos obrigatórios
- [ ] `10.3` Testes unitários: builder payload WPP status update
  - Verificar que `field` é `"messages"` (não `"message_status"`)
  - Verificar presença dos campos `conversation` e `pricing`
- [ ] `10.4` Testes unitários: builder payload Instagram texto — estrutura `messaging`
- [ ] `10.5` Testes unitários: builder payload Instagram delivery receipt (`delivery.mids` + `watermark`)
- [ ] `10.5b` Testes unitários: builder payload Instagram read receipt (`read.watermark`)
- [ ] `10.6` Testes unitários: geração de `X-Hub-Signature-256`
- [ ] `10.7` Testes unitários: fluxo de verificação `GET /webhook/{canal}`
  - Token correto → 200 + challenge
  - Token errado → 403
  - `hub.mode` diferente de `subscribe` → 403
- [ ] `10.8` Testes de integração: `PATCH /config/{canal}` — sucesso, campos inválidos, canal inválido
- [ ] `10.9` Testes de integração: `DELETE /history/{canal}`
- [ ] `10.10` Testes de integração: `POST /callback/{canal}` — sucesso, payload malformado, canal inválido
- [ ] `10.11` Testes de integração: envio ao webhook — simular 200, 500 e timeout
- [ ] `10.12` Cobertura mínima: 80%

---

### ÉPICO 11 — CI/CD e publicação

- [ ] `11.1` GitHub Actions `test.yml` — testes em todo push e PR
- [ ] `11.2` GitHub Actions `lint.yml` — linting e formatação em todo push e PR
- [ ] `11.3` GitHub Actions `docker-publish.yml` — publicar imagem ao criar tag `v*.*.*`
  - Build multi-platform: `linux/amd64` e `linux/arm64`
  - Push para registro escolhido em D3
- [ ] `11.4` Badges no README: CI · Docker pulls · image size · license
- [ ] `11.5` `CHANGELOG.md` com formato Keep a Changelog

---

### ÉPICO 12 — Documentação pública

- [ ] `12.1` `README.md` completo (ver seção separada no repositório)
- [ ] `12.2` `CONTRIBUTING.md` — como rodar localmente, abrir PR, convenção de commits
- [ ] `12.3` `LICENSE`
- [ ] `12.4` `.github/ISSUE_TEMPLATE/` — bug report e feature request
- [ ] `12.5` `docker-compose.example.yml` — exemplo de uso com aplicação consumidora

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
| D2 | Persistência de config | Apenas memória · `config.json` local | Define `2.1` e UX do `7.10` |
| D3 | Registro Docker | Docker Hub · GitHub Container Registry | Define `11.3` |
| D4 | Licença | MIT · Apache 2.0 | Define `12.3` |
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
