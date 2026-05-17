# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.1] — 2026-05-17

### Added

- Media upload route and media file serving
- Instagram channel: outbound media (image / audio / video)
- Configurable `phone_number_id`, in-app docs panel and UX improvements
- Automatic restoration of channel config fields from `localStorage`
- Support for `audio/webm` and `video/webm` as valid media types

### Fixed

- Media send now uses Meta's `id` reference instead of `link`
- Debug panel correctly shows both outbound and inbound payloads
- Lint and broken test scenarios in CI
- `MediaRecorder` no longer uses `timeslice`, producing complete WebM blobs

### Changed

- Microphone affordance migrated from emoji to Material SVG icon
- Codebase formatted with Black to match the CI check
- Container image now published to `ghcr.io/dimmykarson/wig` (was Docker Hub)
- `.coverage` and coverage artifacts removed from version control

### Security

- `python-dotenv` 1.0.1 → 1.2.2 (GHSA-mf9w-mj56-hr94)
- `python-multipart` 0.0.9 → 0.0.28 (GHSA-59g5-xgcq-4qw3, -wp53-j4wj-2cfg, -mj87-hwqh-73pj, -pp6c-gr5w-3c5g)
- `fastapi` 0.115.0 → 0.136.1 (unblocks `starlette` ≥0.46 → 1.0.0, fixing GHSA-f96h-pmfr-66vw, -2c2j-9gv5-cj73, -7f5h-v6xp-fcq8)

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
[0.1.1]: https://github.com/dimmykarson/wig/releases/tag/v0.1.1
[Unreleased]: https://github.com/dimmykarson/wig/compare/v0.1.1...HEAD
