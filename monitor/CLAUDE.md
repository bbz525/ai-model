# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Baby safety monitoring system that uses motion detection + local Ollama vision model to detect dangerous infant behaviors, then triggers alerts via QQ bot and TTS voice announcements.

## Running the System

The system has two components that run separately:

**1. QQ Bot (official API mode):**
```bash
python qq_bot/client.py
# or legacy standalone script:
python qq_chat.py
```

**2. Main detector:**
```bash
python img_detect.py
# or using the monitor package:
python -m monitor
```

The detector communicates with the QQ bot via HTTP on `127.0.0.1:8083` (default `QQ_HTTP_PORT`).

## Configuration

All config is via `.env` (copy `.env.example`). Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `CAMERA_URL` | `http://192.168.1.13:8081` | Camera stream URL (RTSP/HTTP/`0` for USB) |
| `OLLAMA_API` | `http://127.0.0.1:11434/api/generate` | Local Ollama endpoint |
| `MODEL_NAME` | `qwen3.5` | Vision model name in Ollama |
| `QQ_BOT_TYPE` | `official` | `official` (QQ Open Platform) or `napcat` (NapCat/go-cqhttp) |
| `QQ_OFFICIAL_APPID` / `QQ_OFFICIAL_SECRET` | — | QQ Open Platform credentials |
| `QQ_OFFICIAL_USER_ID` | — | Target user's `user_openid` (obtained from bot logs on first message) |
| `TTS_API_KEY` / `TTS_BASE_URL` | — | MiMo TTS credentials (dmxapi.cn) |

`DETECTION_PROMPT` can be overridden in `.env` to change what the AI monitors for.

## Architecture

```
img_detect.py (legacy monolith)        monitor/ (refactored package)
     │                                      │
     ├── Motion detection (OpenCV)     detection/
     │   frame diff → contours              ├── camera.py   (connect/reconnect)
     │                                      ├── motion.py   (frame diff)
     ├── Ollama vision analysis             └── ollama.py   (call local LLM)
     │   → JSON: {status, confidence,
     │     detection, risk_level}       notification/
     │                                      ├── qq.py       (send via official/napcat)
     ├── Alert dispatch                     └── dispatcher.py (console+QQ+TTS)
     │
     └── TTS voice (MiMo)              tts/
                                            ├── base.py     (AlertLevel, TTSProvider protocol)
                                            ├── mimo.py     (MiMoTTSClient + AlertAnnouncer)
                                            └── voice.py    (VoiceAnnouncer wrapper)
```

**`img_detect.py`** is the original monolith (all logic inline). The `monitor/` package is a refactored version with the same logic split into modules. Both are functional; `monitor/` is the canonical structure going forward.

**QQ bot architecture:** `qq_bot/client.py` runs an `asyncio` bot (via `botpy`) + an `aiohttp` HTTP server on the same event loop. The detector calls `POST /alert` on this HTTP server to push notifications. Users must first send a message to the bot to register their `user_openid` session (TTL: 1 hour).

**Two QQ modes:**
- `official`: Uses QQ Open Platform C2C API — requires `qq_chat.py`/`qq_bot/client.py` running as intermediary
- `napcat`: Uses NapCat/go-cqhttp REST API for group messages — no separate bot process needed

**TTS flow:** `VoiceAnnouncer` (in `monitor/tts/voice.py`) wraps any `TTSProvider`. `MiMoTTSClient` (in `monitor/tts/mimo.py`) implements the protocol using MiMo-V2-TTS via OpenAI-compatible API. Audio plays via `sounddevice`; if unavailable, saves `.wav` files.

**Alert level mapping:** Ollama `risk_level` strings (`low/medium/high/critical`) map to `AlertLevel` enum (`INFO/WARNING/ERROR/CRITICAL`), which controls TTS style (speed, emotion, repeat count).

## Dependencies

Requires: `opencv-python`, `imutils`, `requests`, `python-dotenv`, `botpy`, `aiohttp`, `openai`, `soundfile`, `sounddevice`, `numpy`

Audio playback (`soundfile`/`sounddevice`) is optional — system degrades gracefully to saving `.wav` files.

## Deployment

Deployment documentation is available in the following files:

- **`DEPLOYMENT.md`** - Comprehensive deployment guide with multiple deployment methods
- **`CHECKLIST.md`** - Deployment checklist for verification
- **`deploy.sh`** - Automated deployment script with manual/systemd/docker modes
- **`start.sh`** - Quick start script for development/testing
- **`validate_config.py`** - Configuration validation script
- **Systemd service files**: `monitor-qqbot.service`, `monitor-detector.service`
- **Docker config**: `Dockerfile`, `docker-compose.yml`

### Quick Deployment Commands

```bash
# Validate configuration
python validate_config.py

# Manual deployment (development)
./deploy.sh -m manual

# Systemd service deployment (production)
sudo ./deploy.sh -m systemd

# Docker deployment
./deploy.sh -m docker
docker-compose up -d

# Quick start (after manual deployment)
./start.sh
```
