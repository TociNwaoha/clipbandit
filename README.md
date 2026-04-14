# PostBandit

PostBandit takes long-form videos (podcasts, sermons, YouTube videos) and automatically generates short viral clips with captions. Built for churches and solo creators who want OpusClip-quality output at a fraction of the cost.

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

## Google OAuth Login Config

To enable Google sign-in on `/login`:

- Set `GOOGLE_CLIENT_ID`
- Set `GOOGLE_CLIENT_SECRET`

Required Google Console OAuth redirect URIs:

- `https://postbandit.com/api/auth/callback/google`
- `http://localhost:3001/api/auth/callback/google`

Notes:

- Google login exchanges the Google `id_token` for a backend JWT via `/api/auth/google/login`.
- New Google users are auto-created as `starter` tier.
- Existing email/password login stays unchanged.

## YouTube OAuth Provider Config

To enable real YouTube social connection flow:

- Set `YOUTUBE_CLIENT_ID`
- Set `YOUTUBE_CLIENT_SECRET`
- Set `SOCIAL_TOKEN_ENCRYPTION_KEY` (required for encrypted token storage)
- Set `BACKEND_PUBLIC_URL` to your externally reachable backend URL

Google Cloud OAuth redirect URI must match:

- `{BACKEND_PUBLIC_URL}/api/social/youtube/callback`

If any required field is missing/invalid, `/api/social/providers` returns YouTube as `provider_not_configured` with missing-field diagnostics.

## Facebook Pages Provider Config

To enable real Facebook Pages connection + publishing:

- Set `FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET`
  - or use shared fallback `META_APP_ID` and `META_APP_SECRET`
- Set `SOCIAL_TOKEN_ENCRYPTION_KEY` (required for encrypted token storage)
- Set `BACKEND_PUBLIC_URL` to your externally reachable backend URL
- Optional: set `META_GRAPH_API_VERSION` (default `v21.0`)

Facebook callback URI must match:

- `{BACKEND_PUBLIC_URL}/api/social/facebook/callback`

Notes:

- Facebook integration targets **Pages only** (not personal profiles).
- One OAuth connection may create multiple connected destinations (one per Page).

## Instagram OAuth Provider Config (`instagram_business_basic`)

To enable real Instagram professional-account connection + publishing:

- Set `INSTAGRAM_APP_ID` and `INSTAGRAM_APP_SECRET`
  - or use shared fallback `META_APP_ID` and `META_APP_SECRET`
- Set `SOCIAL_TOKEN_ENCRYPTION_KEY` (required for encrypted token storage)
- Set `BACKEND_PUBLIC_URL` to your externally reachable backend URL
- Ensure your Meta app has **Instagram Login** enabled for this provider flow

Instagram callback URI must match:

- `{BACKEND_PUBLIC_URL}/api/social/instagram/callback`

Notes:

- Instagram provider now uses the Instagram Login model directly (not Facebook `/me/accounts` Page discovery).
- Instagram integration targets **Business/Creator** accounts only.
- Instagram and Facebook are separate provider paths: Facebook handles Pages; Instagram handles Instagram professional account connect/publish.
- If OAuth succeeds but no professional Instagram account is returned, PostBandit fails honestly and asks for reconnect with the correct account.

## Threads Provider Config

To enable real Threads connection + text publishing:

- Set `THREADS_APP_ID` and `THREADS_APP_SECRET`
  - or use shared fallback `META_APP_ID` and `META_APP_SECRET`
- Set `SOCIAL_TOKEN_ENCRYPTION_KEY` (required for encrypted token storage)
- Set `BACKEND_PUBLIC_URL` to your externally reachable backend URL
- Optional: set `THREADS_GRAPH_API_VERSION` (default `v1.0`)

Threads callback URI must match:

- `{BACKEND_PUBLIC_URL}/api/social/threads/callback`

Notes:

- Threads integration is real for connect + text posting in this pass.
- Threads media/video posting is deferred and reported honestly in status metadata.

## X (Twitter) OAuth Provider Config

To enable real X connection + text posting flow:

- Set `X_CLIENT_ID`
- Set `X_CLIENT_SECRET`
- Set `SOCIAL_TOKEN_ENCRYPTION_KEY` (required for encrypted token storage)
- Set `BACKEND_PUBLIC_URL` to your externally reachable backend URL

X developer app callback URI must match:

- `{BACKEND_PUBLIC_URL}/api/social/x/callback`

Notes:

- X posting is text-only in this pass (media/video upload is deferred).
- If X does not return a usable refresh token, connection/publish fails honestly and requires reconnect.

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
