# ClipBandit

ClipBandit takes long-form videos (podcasts, sermons, YouTube videos) and automatically generates short viral clips with captions. Built for churches and solo creators who want OpusClip-quality output at a fraction of the cost.

## Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

## Setup

```bash
git clone <repo>
cd clipbandit
cp .env.example .env
docker-compose up --build
```

## Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

Default login: `admin@clipbandit.com` / `changeme123`

## YouTube OAuth Provider Config

To enable real YouTube social connection flow:

- Set `YOUTUBE_CLIENT_ID`
- Set `YOUTUBE_CLIENT_SECRET`
- Set `SOCIAL_TOKEN_ENCRYPTION_KEY` (required for encrypted token storage)
- Set `BACKEND_PUBLIC_URL` to your externally reachable backend URL

Google Cloud OAuth redirect URI must match:

- `{BACKEND_PUBLIC_URL}/api/social/youtube/callback`

If any required field is missing/invalid, `/api/social/providers` returns YouTube as `provider_not_configured` with missing-field diagnostics.

## 10-Prompt Build Plan

1. **Foundation** — Docker, DB schema, auth, skeleton UI (this prompt)
2. **Video Ingestion** — Upload endpoint, yt-dlp download, R2 storage
3. **Transcription** — faster-whisper integration, word-level timestamps
4. **Clip Scoring** — AI scoring engine, hook/energy detection
5. **Clip Management** — Clip browser UI, score display, filtering
6. **Caption Engine** — FFmpeg burn-in, SRT export, caption styles
7. **Export Pipeline** — Render queue, aspect ratio cropping, download URLs
8. **Dashboard & Analytics** — Stats, usage tracking, tier limits
9. **Payments** — Stripe integration, tier upgrades, usage billing
10. **Production Hardening** — Error handling, monitoring, rate limiting, deploy
