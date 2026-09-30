# NARADHA — Civic Complaint Management Platform

**NARADHA** is a Django-based platform for transparent, AI-assisted civic complaint
management. Citizens file complaints with photographic/video evidence; AI verifies
evidence authenticity and scores priority; reviewers confirm; officials and
ministers resolve issues; and field workers handle on-site verification. SLA
deadlines and automatic escalation keep every complaint moving.

## Features

- **Complaint lifecycle** — 16-stage workflow from draft → submitted → AI-verified →
  human-reviewed → assigned → in progress → field work → citizen verification → resolved,
  with reopen and escalation paths.
- **AI evidence verification** — OpenCV/Pillow based image quality, blur, brightness,
  contrast and EXIF/GPS metadata analysis, with manipulation detection scoring
  (Celery tasks).
- **Priority scoring & smart routing** — urgency/severity/impact scoring and
  load-balanced auto-assignment of officials with routing logs.
- **SLA tracking & escalation** — automatic breach detection and 4-level escalation
  (supervisor → department head → minister → state) via Celery beat.
- **Real-time messaging** — Django Channels WebSocket chat per complaint, plus an
  in-app notification channel with delivery/read receipts.
- **Role-based access** — Citizen, Reviewer, Official, Minister, Field Worker and
  Admin roles enforced through DRF custom permissions.
- **Dashboards & analytics** — public, citizen, official, minister and admin
  dashboards; department/official performance metrics, issue patterns and heatmap data.
- **Citizen portal** — server-rendered multi-step complaint filing with live AI
  status, evidence previews, status timeline, endorsements and on-site sign-off;
  public tracking and community endorsements.
- **Fieldwork module** — task assignment, checklists, GPS tracking of field workers,
  before/after photos and performance metrics.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5, Django REST Framework |
| Auth | SimpleJWT (email login), role-based permissions |
| Real-time | Django Channels 4, ASGI (Daphne) |
| Background jobs | Celery + Redis (in-memory fallback for dev) |
| AI/image | OpenCV, NumPy, Pillow |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Django templates + Tailwind (portal), JSON API (clients) |

## Project Structure

```
naradha_project/
├── manage.py
├── requirements.txt
├── .env.example              # copy to .env
├── naradha/                  # project config
│   ├── settings.py           # env-driven settings
│   ├── urls.py               # API + portal routes
│   ├── asgi.py               # Channels entrypoint
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── users/                # CustomUser, Department, Jurisdiction, permissions
│   ├── complaints/           # Complaint models, API + citizen portal
│   ├── ai_services/          # AI models, Celery tasks (verify/score/route)
│   ├── verification/         # AI + human verification results
│   ├── routing/              # Routing logs & official workloads
│   ├── fieldwork/            # Field tasks, GPS tracking, checklists
│   ├── messaging/            # Conversations, messages, notifications, WS consumers
│   ├── dashboard/            # Dashboard widgets & role dashboards
│   └── analytics/            # Performance metrics, patterns, heatmaps
├── templates/                # Citizen portal (base + complaint pages)
├── scripts/
│   └── seed_data.py          # Demo data loader
└── media/                    # Uploaded evidence (dev)
```

## Quick Start

### 1. Prerequisites

- Python 3.10+ (3.12 recommended)
- (Optional) Redis — only needed for production Channels/Celery; dev uses in-memory layers

### 2. Install dependencies

```bash
cd naradha_project
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

A ready-to-use `.env` (SQLite, `DEBUG=True`) ships with the project, so this
step is optional. To customise:

```bash
cp .env.example .env              # Windows: copy .env.example .env
```

The defaults work out of the box for local development (SQLite, DEBUG=True).
If `DEBUG=False` (production), remember to run `python manage.py collectstatic`
before starting the server — see Troubleshooting below.

### 4. Migrate & seed

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py shell -c "exec(open('scripts/seed_data.py').read())"
```

The seed script creates demo accounts (all with password `naradha123`):

| Role | Email |
|---|---|
| Admin | admin@naradha.example |
| Citizen | citizen@naradha.example |
| Reviewer | reviewer@naradha.example |
| Official | official@naradha.example |
| Minister | minister@naradha.example |
| Field Worker | fieldworker@naradha.example |

### 5. Run the server

```bash
python manage.py runserver
```

- Citizen portal: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/
- API root: http://127.0.0.1:8000/api/

### 6. Optional services (production-like)

```bash
# WebSocket server (dev):
daphne -b 0.0.0.0 -p 8001 naradha.asgi:application

# Celery worker + beat:
celery -A naradha worker -l info
celery -A naradha beat -l info
```

## API Overview

All API endpoints are prefixed with `/api/` and return JSON. Authentication uses
JWT bearer tokens.

| Endpoint | Description |
|---|---|
| `POST /api/auth/register/` | Create an account (citizen / field worker self-registration) |
| `POST /api/auth/token/` * | Obtain JWT pair (email + password) |
| `GET/PATCH /api/auth/profile/` | Own profile |
| `GET /api/complaints/complaints/` | Complaint list (role-filtered) + create |
| `GET /api/complaints/complaints/<id>/` | Complaint detail incl. proofs, history |
| `POST /api/complaints/complaints/<id>/endorse/` * | Endorse a complaint |
| `POST /api/ai/complaints/<id>/verify/` | Trigger AI proof verification |
| `POST /api/ai/complaints/<id>/score/` | Trigger priority scoring |
| `POST /api/ai/complaints/<id>/route/` | Trigger AI routing suggestion |
| `GET /api/fieldwork/tasks/` | Field tasks for the logged-in worker |
| `POST /api/fieldwork/location/update/` | Field worker GPS check-in |
| `GET /api/dashboard/public/` | Public dashboard statistics |
| `GET /api/dashboard/official/` | Official dashboard |
| `GET /api/analytics/comprehensive/` | Aggregated analytics |

\* Routes registered by DRF routers; check `apps/*/urls.py` for the exact list,
or browse `http://127.0.0.1:8000/api/` with the browsable API enabled.

### WebSockets (Channels)

```
ws://<host>/ws/complaints/<complaint_id>/chat/    # per-complaint chat
ws://<host>/ws/notifications/                      # user notifications
```

Messages are JSON: `{"type": "message.send", "content": "..."}` etc. See
`apps/messaging/consumers.py` for the protocol.

## Workflow Statuses

`DRAFT → SUBMITTED → PROOF_RECEIVED → AWAITING_HUMAN_REVIEW → VERIFIED →
NOTIFIED_TO_OFFICIAL → COMMITMENT_PUBLISHED → IN_PROGRESS → AWAITING_FIELD_WORK →
FIELD_WORK_COMPLETED → AWAITING_CITIZEN_VERIFICATION → RESOLVED`

Side paths: `REJECTED`, `REQUEST_MORE_INFO`, `REOPENED`, `ESCALATED`.

## How the Workflow Runs Automatically

1. **Submit** — the citizen portal stages evidence, creates the complaint and
   writes the first audit-trail entry, then dispatches the AI chain.
2. **AI verify + score** (Celery; runs synchronously in dev because
   `CELERY_TASK_ALWAYS_EAGER=True`) — OpenCV evidence analysis produces the AI
   confidence score, NLP analysis computes urgency/severity/sentiment, the
   priority (1–10 → LOW/MEDIUM/HIGH/CRITICAL) is derived, and the **SLA
   deadline is fixed** (independent of any commitment).
3. **Human review** — reviewers log in and work the review queue
   (`/complaints/` for the REVIEWER role), sorted into fast (≥85%), standard
   (60–85%) and high-scrutiny (<60%) lanes by AI confidence. Approve → routing;
   Reject / Request-info → citizen-visible reason on the timeline.
4. **Routing** — the engine maps category → department → jurisdiction → the
   least-busy eligible official, assigns them and logs the routing decision.
5. **Commitment & execution** — the official publishes a public commitment
   date, starts progress, and releases the case to a field worker; the field
   worker completes the job.
6. **Citizen sign-off** — the citizen sees the result, rates it 1–5 and either
   resolves the case (it joins the public commitments feed on the home page)
   or requests re-work (SLA clock resets, back to the same official).
7. **Escalation** — a Celery beat job checks SLA breaches every 30 minutes and
   walks the 4-level escalation ladder.

Every transition above appends an immutable entry to the complaint's status
history, rendered as a timeline on the detail page. Citizens can endorse open
complaints (anonymized) instead of duplicate-filing; the filing wizard warns
about similar nearby issues before submission.

## Key Portal URLs

| URL | Who | Purpose |
|---|---|---|
| `/` | everyone | Public stats + recent official commitments |
| `/file-complaint/` | citizens | 3-step filing wizard (with duplicate warnings) |
| `/complaints/` | role-filtered | Citizens: own + open; Reviewers: review queue; Officials: assigned; Field workers: tasks |
| `/complaints/<id>/` | role-filtered | Detail: evidence previews, AI panel, timeline, workflow actions |
| `/complaints/<id>/action/` | POST | Approve/reject, commit, progress, field work, sign-off, endorse |

## Configuration

Key environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` (shipped `.env`) | Dev/prod switch |
| `SECRET_KEY` | — | Django secret |
| `DATABASE_URL` | SQLite | PostgreSQL connection in prod |
| `CELERY_BROKER_URL` | memory | Redis broker in prod |
| `CHANNEL_BACKEND` | in-memory | `channels_redis.core.RedisChannelLayer` in prod |
| `NARADHA_AI_CONFIDENCE_THRESHOLD` | 70 | Min AI score (%) to auto-pass evidence |
| `NARADHA_DEFAULT_SLA_DAYS` | 14 | Default resolution SLA |

## Running Tests & Checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Notes for Production

1. Set `DEBUG=False`, generate a strong `SECRET_KEY`, and restrict `ALLOWED_HOSTS`.
2. Use PostgreSQL via `DATABASE_URL` and Redis for Channels + Celery.
3. Serve static files with WhiteNoise (`collectstatic`) or a CDN; store uploads
   on object storage by swapping `STORAGES['default']`.
4. Run Daphne/Uvicorn behind a TLS-terminating reverse proxy, and keep a
   `gunicorn` WSGI worker for HTTP if preferred.
5. Schedule `apps.ai_services.tasks.check_sla_breaches` via Celery beat (already
   configured every 30 minutes).

## Troubleshooting

**`ValueError: Missing staticfiles manifest entry for 'rest_framework/...'`
(HTTP 500 on API pages such as `/api/auth/register/`)**

Happens when `DEBUG=False` (e.g. no `.env` file — `DEBUG` defaults to off) and
`python manage.py collectstatic` was never run, so WhiteNoise cannot resolve
hashed static URLs. Fixes, in order of preference:

1. For local development create a `.env` with `DEBUG=True` (a ready `.env`
   ships with the project).
2. For production run `python manage.py collectstatic` **before** starting the
   server, then restart it (WhiteNoise scans `STATIC_ROOT` once at startup).

The project's default production static backend is now
`whitenoise.storage.CompressedStaticFilesStorage`, which never raises this
class of 500 — it serves gzip-compressed files without a manifest. If you want
hashed cache-busting filenames instead, switch the `staticfiles` backend in
`naradha/settings.py` to `whitenoise.storage.CompressedManifestStaticFilesStorage`
and make sure `collectstatic` runs on every deploy.

**`TypeError: Field.clean() takes 2 positional arguments but 3 were given`
(`apps/complaints/forms.py`, when uploading evidence)**

This was a bug in an earlier version of `MultipleFileField` — it called
`super(forms.FileField, self).clean(f, initial)`, which skips
`FileField.clean()` and hits `Field.clean(value)`. It is fixed by following the
official Django multi-file pattern (`single_file_clean = super().clean`).
If you still run old code, replace the `clean()` method of `MultipleFileField`
accordingly.

**Evidence uploaded at step 2 disappears when the complaint is created**

Also fixed: step-2 uploads are now staged under `media/staged_uploads/<uuid>/`
(in session-tracked metadata) and attached when the complaint is finally
submitted at step 3. Abandoned uploads are purged automatically after 24 hours.
Per-file size is validated against `NARADHA_MAX_PROOF_SIZE_MB` (default 10 MB)
and MIME types map onto the `PHOTO` / `VIDEO` / `AUDIO` / `DOCUMENT` choices.

**`Not Found: /favicon.ico` warnings**

Harmless; the base template now ships an inline SVG favicon so browsers no
longer request `/favicon.ico`.

**Windows: `ZoneInfoNotFoundError` for `Asia/Kolkata`**

Install the tz database: `pip install tzdata` (already listed in
`requirements.txt` for Windows platforms).

## License

This project is provided as-is for evaluation and development purposes.
