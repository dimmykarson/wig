# wig — WhatsApp & Instagram Gateway (Mock)

> Mock genérico e configurável de WhatsApp e Instagram para desenvolvimento e testes de integrações Meta Webhooks.

[![CI](https://github.com/dimmykarson/wig/actions/workflows/test.yml/badge.svg)](https://github.com/dimmykarson/wig/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/dimmykarson/wig)](https://hub.docker.com/r/dimmykarson/wig)

---

## O que é

**wig** simula dois celulares em uma página web — um com interface do WhatsApp, outro do Instagram. Você digita mensagens como se fosse um usuário real e o mock encaminha os eventos para a URL de webhook da sua aplicação no formato oficial da Meta.

Quando sua aplicação responde, a resposta aparece no chat simulado em tempo real.

Tudo é configurável pela própria interface: URL do webhook, nome do contato e identificador. Nenhum arquivo de configuração, nenhum restart.

---

## Para que serve

- Testar bots e fluxos de atendimento sem conta Meta Business real
- Desenvolver integrações localmente sem expor portas para a internet
- Inspecionar os payloads exatos trafegados em ambos os sentidos
- Rodar em CI para testes de integração de ponta a ponta

---

## Quickstart

```bash
docker run -p 5504:5504 dimmykarson/wig
```

Acesse [http://localhost:5504](http://localhost:5504) e configure os canais.

---

## Como usar

### 1. Configure cada canal

Clique no ícone ⚙ no cabeçalho de cada celular e preencha:

| Campo | Descrição | Exemplo |
|---|---|---|
| **Webhook URL** | URL da sua aplicação que recebe os eventos | `http://localhost:8000/api/webhook/` |
| **Nome do contato** | Nome do remetente simulado | `João Silva` |
| **Identificador** | Número E.164 (WPP) ou `@handle` (Instagram) | `5586999990000` / `@joaosilva` |

### 2. Copie a URL de callback

Após salvar, o painel exibe a **URL de callback** que você deve configurar na sua aplicação:

```
http://localhost:5504/callback/whatsapp
http://localhost:5504/callback/instagram
```

Quando sua aplicação quiser responder a uma mensagem, ela deve fazer um `POST` para essa URL.

### 3. Envie e receba mensagens

Digite no campo de texto do celular simulado e pressione Enter. O mock encaminha para o webhook da sua aplicação e exibe a resposta no chat assim que ela chegar.

---

## Contrato de API

### Callback — como sua aplicação responde

Faça um `POST` para `/callback/whatsapp` ou `/callback/instagram` com:

```json
{
  "text": "Olá! Como posso ajudar?",
  "type": "text"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `text` | string | sim | Texto da resposta |
| `type` | string | não | Tipo da mensagem (padrão: `"text"`) |

Resposta de sucesso: `200 {"ok": true}`

---

### Payloads enviados ao seu webhook

#### WhatsApp

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
          "id": "wamid.mock_a1b2c3d4e5f6g7h8",
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

#### Instagram

```json
{
  "object": "instagram",
  "entry": [{
    "id": "MOCK_IG_ACCOUNT_ID",
    "messaging": [{
      "sender": { "id": "mock_sender_123" },
      "recipient": { "id": "MOCK_IG_PAGE_ID" },
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

### Demais endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check |
| `GET` | `/info` | URLs de callback e status dos canais |
| `GET` | `/config` | Configuração atual dos dois canais |
| `PATCH` | `/config/{canal}` | Atualiza configuração em runtime |
| `DELETE` | `/history/{canal}` | Limpa histórico do canal |
| `POST` | `/callback/{canal}` | Recebe resposta da aplicação |
| `WS` | `/ws/{canal}` | WebSocket bidirecional (UI ↔ backend) |

`{canal}`: `whatsapp` ou `instagram`

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `5504` | Porta do servidor |
| `MOCK_BASE_URL` | `http://localhost:5504` | URL pública do mock — usada para gerar a callback URL exibida na UI |
| `LOG_LEVEL` | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_DEBUG_ENTRIES` | `50` | Máximo de entradas no painel de debug por canal |

---

## Docker Compose

Exemplo de uso junto com sua aplicação:

```yaml
services:
  wig:
    image: dimmykarson/wig
    ports:
      - "5504:5504"
    environment:
      MOCK_BASE_URL: http://wig:5504   # URL interna na rede Docker
    networks:
      - app

  web:
    build: .
    environment:
      # configure o webhook na sua aplicação para apontar para o wig
      WHATSAPP_WEBHOOK_SECRET: qualquer-coisa
    networks:
      - app

networks:
  app:
```

> **Atenção com redes Docker:** se sua aplicação e o wig rodam no mesmo `docker-compose`, use o nome do serviço (`wig`) como host na Webhook URL. Defina `MOCK_BASE_URL=http://wig:5504` para que a callback URL exibida na UI também seja acessível pela sua aplicação.

> **Acessando de fora (ngrok/tunnel):** se precisar expor o mock para webhooks externos, use um tunnel e defina `MOCK_BASE_URL` com a URL pública gerada.

---

## Painel de debug

Cada celular tem um card de debug colapsável que exibe, para cada mensagem:

- `→ ENVIADO` — payload JSON completo enviado ao webhook da sua aplicação
- `← RECEBIDO` — JSON recebido no callback, com status HTTP
- `✕ ERRO` — detalhes de timeout, connection refused ou resposta não-2xx

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
python -m uvicorn main:app --reload --port 5504
```

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre como abrir PRs e a convenção de commits.

---

## Licença

[MIT](LICENSE)
