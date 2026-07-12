# MyHerzen

MyHerzen is an independent, open-source application for students of the Herzen
State Pedagogical University of Russia. It combines schedules, study groups,
homework, notifications and optional AI assistants across iOS, Android and web.

The repository is intended to remain maintainable by Herzen students. A fresh
installation starts with an empty database; transferring existing user accounts
is not required.

## Open for use and continuation

MyHerzen is open for use, self-hosting, study, modification and continued
development under the Apache License 2.0. Herzen students and student teams are
welcome to clone or fork the repository, deploy their own installation and keep
the official student service alive after the original maintainer leaves.

The project is deliberately documented so that a new team can start with an
empty database and its own server, domains, OAuth applications, Ollama model and
email provider. No private user-account database or access to the original
maintainer's infrastructure is required to continue development.

## Components

- `API/` — FastAPI, SQLAlchemy and PostgreSQL backend;
- `Android/` — Kotlin and Jetpack Compose application;
- `iOS/` — SwiftUI application, widgets and Live Activities;
- `Web/` — static public website and account pages;
- `tests/` — backend test suite.

## Start the backend locally

Requirements:

- Docker Desktop, Docker Engine or another Docker Compose-compatible runtime;
- Git;
- ports `8000` and PostgreSQL's internal container network available.

```bash
git clone https://github.com/MoonbayStudio/MyHerzen.git
cd MyHerzen
make setup
```

Open `.env` and work through it from top to bottom. Every external dependency is
listed there: PostgreSQL, public URLs, the Herzen API, Apple/Google OAuth,
Ollama, SMTP, feature switches and mobile integrity checks. At minimum, replace
`DATABASE_PASSWORD`, `JWT_SECRET`, `FRONTEND_BASE_URL`, `OWNER_EMAILS` and
`ADMIN_EMAILS`. Optional integrations can remain empty or disabled. Then start
the services:

```bash
make up
curl http://127.0.0.1:8000/health
```

The expected response is:

```json
{"status":"healthy"}
```

API documentation is available at <http://127.0.0.1:8000/docs>. AI, SMTP and
third-party sign-in are optional and disabled or left unconfigured in the basic
local setup.

For an internet-facing server, publish only TCP ports `80` and `443` through a
TLS reverse proxy. Keep API port `8000`, PostgreSQL and Ollama closed to the
public internet. The complete server and firewall procedure is in
[SETUP.md](docs/SETUP.md).

Useful commands:

```bash
make status
make logs
make down
make backup
make restore FILE=backups/myherzen-YYYYMMDD-HHMMSS.sql
```

## Documentation

- [Installation and configuration](docs/SETUP.md)
- [Operations, database backup and recovery](docs/OPERATIONS.md)
- [Project handover checklist](docs/HANDOVER.md)
- [Current development progress](PROGRESS.md)

## Development

Backend tests use an isolated SQLite database and do not require the Docker
stack:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Android requires JDK 17 and Android SDK 34:

```bash
cd Android
./gradlew assembleDebug
```

The iOS project is opened from `iOS/MyHerzen.xcodeproj`. Building a distributable
app requires an Apple Developer team and replacement bundle identifiers.

## Production note

The Compose configuration binds the API to `127.0.0.1` by default. In
production, keep that binding and place a TLS reverse proxy such as Caddy or
nginx in front of it. Do not commit `.env`, database dumps, OAuth credentials or
signing keys.

## License

Licensed under the [Apache License 2.0](LICENSE).
