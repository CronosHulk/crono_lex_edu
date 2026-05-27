# CronoLex

domain теперь построен как `FastAPI` backend с Telegram-ботом, admin web и client web в роли тонких клиентов.
Runtime разделён на сервисы `app-api`, `app-bot`, публичный `caddy`, пользовательскую web-морду `web-client` и админскую web-морду `web-admin`.
Backend является источником бизнес-логики, состояния учебных сессий и API-контрактов под админку, Telegram и клиентский web-интерфейс.

## Текущая архитектура

- `app/main.py` собирает `FastAPI` приложение
- `app/api_main.py` запускает API runtime
- `app/bot_main.py` запускает Telegram bot runtime
- `app/api.py` публикует backend API
- `app/composition/root.py` является тонкой точкой сборки backend runtime: создаёт `Database`, `DispatchLock` и последовательно подключает runtime wiring
- `app/composition/*.py` содержит helper wiring для billing, client API, reminders, user import, reference runtime и scheduled runtime
- `app/data_access/provider.py` собирает ORM `SessionManager`, миграции и typed repository accessors для backend runtime; бизнес-фасадные методы живут вне provider
- `app/application/`, `app/composition/*.py`, `app/admin_api/**/services/`, `app/user_import/services/*` и аналогичные live-модули являются специализированным service/runtime layer; тонкие entrypoints/adapters — это routers/API modules/bot runtime modules (`app/api.py`, `app/**/router.py`, `app/bot_runtime/*` и т.п.)
- `app/application/` содержит application services и общие runtime adapters
- `app/domain/`, `app/reference/` и `app/models/` содержат domain logic, reference catalogs и ORM models
- `app/external_providers/` изолирует adapters к внешним AI/TTS/calendar/provider integrations
- `app/billing/` и `app/subscriptions/` содержат billing/subscription domain и runtime modules
- `app/acl/` содержит access-control permissions и processor support
- `app/marketing/` и `app/helpers/` содержат marketing runtime settings и shared helper utilities
- `app/api_helpers/`, `app/validation/`, `app/validators/`, `app/security/`, `app/serialization/` и `app/support/` содержат shared API helpers, validation/security/serialization utilities и support runtime settings
- `Caddyfile` описывает публичный reverse proxy для `https://domain.uno`
- `client_web/` содержит React/Vite client SPA, которая собирается в отдельный `web-client` container
- `admin_web/` содержит React/Vite admin SPA, которая собирается в отдельный `web-admin` container
- `migrations/` хранит каноническую схему и seed новой словарной модели `dictionary_entry`
- локальные audio assets словаря подключаются отдельно от runtime-кода
- техническая документация ведётся отдельно от runtime repo во внешнем CronosVault `Documentation/domain`

## Что умеет бот

- приветствие на украинском языке в официальном тоне
- направляющее приветствие с подсказкой, что выбор делается через нижнее меню Telegram
- выбор уровня английского `A1-C2`
- выбор количества слов в подходе: `10`, `15`, `20`
- нижнее меню Telegram (`reply keyboard`) для:
  - перехода в выбор уровня
  - перехода в выбор режима обучения
  - запуска занятия
- запуск учебной сессии по выбранному уровню
- карточки слов с:
  - озвучкой
  - словом
  - частями речи через запятую
  - американской транскрипцией
  - украинским переводом
  - примерами использования
  - категориями слова после примера
- действия на карточке:
  - `Я вже знаю слово`
  - `Далі`
- последовательные упражнения:
  - `EN -> UK`
  - `UK -> EN`
  - `fill in the gap`
- подбор distractors по embedding-близости из `dictionary_entry.embedding`
- повтор ошибки в конце упражнения
- сохранение повторно ошибочного слова в приоритет повторения
- итоговую статистику по трём упражнениям
- прощание и переход к следующему занятию
- ежедневные reminder-уведомления с действиями `Почати тренування`, `Відкласти на годину` и `Пропустити день`
- `Пропустити день` помечает только текущее reminder-уведомление как `skipped` и возвращает пользователя на главный экран; будущие уведомления продолжают работать по расписанию
- переход в web-настройки через magic link; детальная форма настроек живёт в `client_web`
- в `client_web` список изучаемых слов позволяет поднять слово в очередь следующего занятия только после первых десяти позиций текущего списка

## База данных

Кроме уже существующих таблиц пользователей и словаря теперь используются:

- `user_learning_settings`
- `user_reminder_weekday`
- `user_word_progress`
- `learning_session`
- `learning_session_word`
- `learning_answer`

Это позволяет:

- хранить пользовательские настройки обучения
- хранить отдельный набор дней недели для reminder-механизма
- вести состояние активной сессии и интервалы повторения
- помнить прогресс по каждому слову
- собирать ответы для статистики и будущей аналитики в админке

GitLab pipeline теперь делает перед deploy:

- backend quality gate: `.venv/bin/python -m ruff check app tests word_base`, затем полный `.venv/bin/python -m pytest`
- Docker-only frontend gate для `admin_web`: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test:coverage` выполняются внутри `node:22-alpine`, без `node_modules` на host checkout
- пересборку default `cpu-only` сервисов перед `up --no-build`: `app-api`, `app-bot`, `app-import-scheduler`, `app-billing-reconciliation`, `app-subscription-maintenance`, `app-embedding-worker`, `web-admin`, `web-client`
- очистку Docker image/build cache до сборки; после сборки очищается только build cache, чтобы `up --no-build` не потерял свежие локальные образы
- удаление agent config files (`agents/`, `.agents/`) из серверного checkout после `git pull`; в git они остаются

Для этого в `docker-compose.yml`:

- `caddy` открывает порты `80` и `443` и автоматически получает/обновляет TLS certificate для `domain.uno`
- `web-client` отвечает за пользовательскую web-страницу на `https://domain.uno`
- `web-admin` отвечает за React admin SPA на `https://domain.uno/admin`
- сервисы приложения называются `app-api`, `app-bot`, `app-import-scheduler`, `app-billing-reconciliation`, `app-subscription-maintenance` и `app-embedding-worker`
- у runtime-сервисов включён `restart: unless-stopped`
- `app-api` стартует после `postgres` healthcheck
- `app-api` настроен на один worker: client-web import SSE события идут через local broker внутри API-процесса
- `app-bot` стартует после готовности `postgres` и `app-api`
- `app-bot` exposes `8080` for Telegram webhook callbacks; Caddy reverse proxies `/telegram/webhook` to it
- healthcheck `app-api` проверяет `http://127.0.0.1:8000/api/v1/health`
- `app-database-backup` ежедневно в `00:00` по `APP__TIMEZONE` делает зашифрованный `pg_dump -Fc` всей PostgreSQL DB в `./database_backup`
- embedding-зависимости не входят в базовую backend-сборку; `app-embedding-worker` собирается отдельным `Dockerfile.embeddings` image с `torch` и `sentence-transformers`
- `app-embedding-worker` стартует вместе с deploy, ежедневно в `APP__USER_IMPORT_EMBEDDING_BUILD_HOUR` запускает embedding phase и после завершения засыпает до следующего запуска
- для embedding worker используется persistent volume `huggingface_cache`
- для `caddy` используются persistent volumes `caddy_data` и `caddy_config`
- scheduled audio phase теперь не только двигает approved pending words дальше по pipeline, но и remediation-обновляет старые словарные записи без `audio_path`; `super_admin` получает отдельный `admin:audio-summary` notice по batch и backlog
- intake summary по bind/import хранит generated txt artifacts рядом с `storage_path` import job: `*_queued_words.txt`, `*_existing_words.txt`, а downstream publish использует `*_published_words.txt`; для `invalid` отдельный txt-файл не создаётся, список остаётся тільки на safe screen/report

Для автоматического TLS у `Caddy` домен `domain.uno` должен уже резолвиться на сервер, где открыт входящий `80/443`.

