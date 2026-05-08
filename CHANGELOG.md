# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.0] — 2026-05-08

### Added

- Two simulated phone interfaces side by side: WhatsApp (dark theme) and Instagram (light theme)
- Full Meta Webhooks payload fidelity for WhatsApp Cloud API and Instagram Platform
  - WPP text message payload with all required fields (`waba_id`, `phone_number_id`, etc.)
  - WPP status update with `field: "messages"`, `conversation` and `pricing` blocks
  - Instagram text payload using `messaging` array structure
  - Instagram delivery receipt (`delivery.mids` + `watermark`)
  - Instagram read receipt (`read.watermark`)
- `X-Hub-Signature-256` signing via HMAC-SHA256 on every outgoing webhook POST
- Hub challenge verification flow (`GET /webhook/{canal}`)
- Callback endpoint (`POST /callback/{canal}`) for application replies
- Simulated delivery and read status updates with configurable delays
- Real-time WebSocket communication between UI and server
  - Exponential backoff reconnection (1s → 2s → 4s → … → 30s)
  - Keepalive ping every 25s
  - Server-side inactivity timeout (5 min, configurable via `WS_INACTIVITY_TIMEOUT_S`)
- Configuration panel per channel: webhook URL, contact name, identifier
- Read-only info boxes: callback URL, webhook verification URL, verify token, app secret
- Debug panel with syntax-highlighted JSON payloads, HTTP status codes and copy button
- Config persistence in `config.json` — survives server restarts
- All settings configurable via environment variables (see `.env.example`)
- Docker image (multi-platform `linux/amd64` + `linux/arm64`) ready for Docker Hub
- 68 unit and integration tests, 98% code coverage

[0.1.0]: https://github.com/dimmykarson/wig/releases/tag/v0.1.0
[Unreleased]: https://github.com/dimmykarson/wig/compare/v0.1.0...HEAD
