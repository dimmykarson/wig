# wig — WhatsApp & Instagram Gateway (Mock)

> Mock genérico e configurável de WhatsApp e Instagram para desenvolvimento e testes de integrações Meta Webhooks.

[![CI](https://github.com/dimmykarson/wig/actions/workflows/test.yml/badge.svg)](https://github.com/dimmykarson/wig/actions/workflows/test.yml)
[![Lint](https://github.com/dimmykarson/wig/actions/workflows/lint.yml/badge.svg)](https://github.com/dimmykarson/wig/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Container](https://img.shields.io/badge/container-ghcr.io-2088FF?logo=github)](https://github.com/dimmykarson/wig/pkgs/container/wig)

---

## O que é

**wig** simula dois celulares em uma página web — um com interface do WhatsApp, outro do Instagram. Você digita mensagens, envia arquivos ou grava áudio como se fosse um usuário real; o mock encaminha os eventos para a URL de webhook da sua aplicação no formato oficial da Meta.

Quando sua aplicação responde via callback, a resposta aparece no chat simulado em tempo real.

Tudo é configurável pela própria interface: URL do webhook, nome do contato, identificador e Phone Number ID. Nenhum arquivo de configuração, nenhum restart. As configurações são persistidas no servidor e restauradas automaticamente no próximo acesso.

---

## Para que serve

- Testar bots e fluxos de atendimento sem conta Meta Business real
- Desenvolver integrações localmente sem expor portas para a internet
- Simular envio de texto, imagens, documentos e áudio (gravado pelo microfone)
- Inspecionar os payloads exatos trafegados em ambos os sentidos via painel de debug em tempo real
- Rodar em CI para testes de integração de ponta a ponta

---

## Quickstart

```bash
docker run -p 5504:5504 ghcr.io/dimmykarson/wig:latest
```

Acesse [http://localhost:5504](http://localhost:5504) e configure os canais.

---

## Como usar

### 1. Configure cada canal

Clique no ícone ⚙ no cabeçalho de cada celular e preencha:

#### WhatsApp

| Campo | Descrição | Exemplo |
|---|---|---|
| **Webhook URL** | URL da sua aplicação que recebe os eventos | `http://localhost:8000/api/webhook/` |
| **Nome do contato** | Nome do remetente simulado | `João Silva` |
| **Número (E.164)** | Identificador numérico — usado como `wa_id` nos payloads | `5586999990000` |
| **Phone Number ID** | ID do número cadastrado no painel Meta — vai em `metadata.phone_number_id` | `102938475610293` |

#### Instagram

| Campo | Descrição | Exemplo |
|---|---|---|
| **Webhook URL** | URL da sua aplicação que recebe os eventos | `http://localhost:8000/api/webhook/` |
| **Nome do contato** | Nome do remetente simulado | `Maria` |
| **IGSID** | Identificador numérico do usuário no Instagram | `123456789` |

> **Dica:** os campos são salvos no navegador e restaurados automaticamente na próxima vez que você abrir a página. Use o botão **↩ Restaurar** para repopular os campos manualmente a qualquer momento.

### 2. Copie a URL de callback

Após salvar, o painel exibe a **URL de callback** que você deve configurar na sua aplicação:

```
http://localhost:5504/callback/whatsapp
http://localhost:5504/callback/instagram
```

O endpoint também aceita o identificador do canal no lugar do nome (`/callback/5586999990000` ou `/callback/123456789`), que é o formato enviado por algumas integrações.

### 3. Envie mensagens

Use o campo de texto para digitar e pressione Enter (ou clique em ➤).

**Enviar mídia:**
- Clique em **📎** para selecionar uma imagem ou documento
- Após selecionar o arquivo, uma barra de preview aparece — escreva uma legenda (opcional) e clique em ➤

**Gravar áudio:**
- Clique no botão 🎤 para iniciar a gravação
- Clique novamente para enviar, ou em **Cancelar** para descartar

---

## Contrato de API

### Callback — como sua aplicação responde

Faça um `POST` para `/callback/whatsapp` ou `/callback/instagram` com:

```json
{
  "type": "text",
  "text": "Olá! Como posso ajudar?"
}
```

Para responder com mídia:

```json
{
  "type": "image",
  "text": "https://sua-app/imagens/confirmacao.png",
  "caption": "Pedido confirmado!"
}
```

```json
{
  "type": "document",
  "text": "https://sua-app/docs/contrato.pdf",
  "filename": "contrato.pdf",
  "caption": "Segue o contrato em anexo."
}
```

Campos aceitos:

| Campo | Tipo | Descrição |
|---|---|---|
| `type` | `text` \| `image` \| `audio` \| `video` \| `document` | Tipo da mensagem |
| `text` | string | Texto (para `type=text`) ou URL da mídia |
| `caption` | string | Legenda da mídia (opcional) |
| `filename` | string | Nome do arquivo (para `document`) |

Resposta de sucesso: `200 {"ok": true}`

---

### Payloads enviados ao seu webhook

Os payloads são **idênticos ao formato oficial da Meta**, incluindo o header de assinatura.

**Header enviado em todas as requisições:**
```
X-Hub-Signature-256: sha256=<HMAC-SHA256(APP_SECRET, raw_body)>
```

Configure `APP_SECRET` no mock com o mesmo valor que sua aplicação usa para validar a assinatura.

#### WhatsApp — mensagem de texto

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
          "phone_number_id": "102938475610293"
        },
        "contacts": [{ "profile": { "name": "João Silva" }, "wa_id": "5586999990000" }],
        "messages": [{
          "from": "5586999990000",
          "id": "wamid.HBgLmock1a2b3c4d5e6f",
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

#### WhatsApp — mensagem de mídia (imagem, documento, áudio)

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
          "phone_number_id": "102938475610293"
        },
        "contacts": [{ "profile": { "name": "João Silva" }, "wa_id": "5586999990000" }],
        "messages": [{
          "from": "5586999990000",
          "id": "wamid.HBgLmock1a2b3c4d5e6f",
          "timestamp": "1746700000",
          "type": "image",
          "image": {
            "id": "abc123.jpg",
            "mime_type": "image/jpeg",
            "caption": "Foto do produto"
          }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

O campo `id` da mídia corresponde ao nome do arquivo. Para baixar, use:
```
GET /media/{id}
```

#### WhatsApp — status updates

O mock dispara status updates automaticamente após o envio (simulando o comportamento real):

| Status | Delay padrão |
|---|---|
| `delivered` | 1 segundo |
| `read` | 3 segundos |

Delays configuráveis via env vars `STATUS_DELIVERED_DELAY_MS` e `STATUS_READ_DELAY_MS`.

---

#### Instagram — mensagem de texto

> A estrutura do Instagram é diferente do WhatsApp — usa `messaging` direto no `entry`, sem a camada `changes`.

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
        "mid": "mid.$mock1a2b3c4d5e6f7g8h",
        "text": "mensagem do usuário"
      }
    }]
  }]
}
```

O mock também envia delivery receipt e read receipt automaticamente.

---

### Verificação de webhook

```
GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<random>
GET /webhook/instagram?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<random>
```

- Token correto → `200` com o valor de `hub.challenge` em texto puro
- Token errado → `403 Forbidden`

---

### Todos os endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check |
| `GET` | `/info` | URLs de callback, verificação e WebSocket |
| `GET` | `/config` | Configuração atual dos dois canais |
| `PATCH` | `/config/{canal}` | Atualiza configuração em runtime |
| `DELETE` | `/history/{canal}` | Limpa histórico do canal |
| `GET` | `/webhook/{canal}` | Fluxo de verificação de webhook (hub.challenge) |
| `POST` | `/callback/{canal}` | Recebe resposta da aplicação (`canal` = nome ou identificador) |
| `POST` | `/media/upload` | Faz upload de um arquivo de mídia |
| `GET` | `/media/{name}` | Serve um arquivo de mídia enviado |
| `WS` | `/ws/{canal}` | WebSocket bidirecional (UI ↔ backend) |

`{canal}`: `whatsapp`, `instagram`, ou o identificador configurado (ex.: `5586999990000`).

**Tipos de mídia aceitos no upload:** `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `audio/mpeg`, `audio/ogg`, `audio/wav`, `audio/mp4`, `audio/aac`, `audio/webm`, `video/mp4`, `video/webm`, `video/3gpp`, `application/pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`.

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `5504` | Porta do servidor |
| `MOCK_BASE_URL` | `http://localhost:5504` | URL pública do mock — usada para gerar as URLs exibidas na UI e nos uploads |
| `APP_SECRET` | `mock-secret` | Chave para assinar payloads com `X-Hub-Signature-256` |
| `VERIFY_TOKEN` | `mock-verify-token` | Token para o fluxo de verificação de webhook |
| `LOG_LEVEL` | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_DEBUG_ENTRIES` | `50` | Máximo de entradas no painel de debug por canal |
| `STATUS_DELIVERED_DELAY_MS` | `1000` | Delay para status "delivered" no WPP (ms) |
| `STATUS_READ_DELAY_MS` | `3000` | Delay para status "read" / read receipt (ms) |
| `WS_INACTIVITY_TIMEOUT_S` | `300` | Tempo de inatividade do WebSocket antes de fechar (segundos) |

---

## Docker Compose

Exemplo de uso junto com sua aplicação:

```yaml
services:
  wig:
    image: ghcr.io/dimmykarson/wig:latest
    ports:
      - "5504:5504"
    environment:
      MOCK_BASE_URL: http://wig:5504   # URL interna na rede Docker
    networks:
      - app

  web:
    build: .
    networks:
      - app

networks:
  app:
```

> **Atenção com redes Docker:** se sua aplicação e o wig rodam no mesmo `docker-compose`, use o nome do serviço (`wig`) como host na Webhook URL. Defina `MOCK_BASE_URL=http://wig:5504` para que a callback URL exibida na UI também seja acessível pela sua aplicação.

> **Acessando de fora (ngrok/tunnel):** se precisar expor o mock para webhooks externos, use um tunnel e defina `MOCK_BASE_URL` com a URL pública gerada.

---

## Painel de debug

Cada celular tem um card de debug colapsável que exibe em tempo real, via WebSocket, cada evento processado:

| Indicador | Descrição |
|---|---|
| `→ ENVIADO` | Payload JSON completo enviado ao webhook da sua aplicação |
| `← RECEBIDO` | JSON recebido no callback, com status HTTP |
| `⚡ STATUS` | Status updates (delivered/read) enviados ao webhook |
| `✕ ERRO` | Detalhes de timeout, connection refused ou resposta não-2xx |

Botões disponíveis: **Copiar JSON** por entrada · **Limpar log**

---

## Desenvolvendo localmente

```bash
git clone https://github.com/dimmykarson/wig.git
cd wig
cp .env.example .env

# com Docker
docker compose up

# sem Docker (após instalar dependências)
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 5504
```

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre como abrir PRs e a convenção de commits.

---

## Licença

[MIT](LICENSE)
