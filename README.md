# rentico-news

Ежедневная сводка транспортных новостей Дубая и ОАЭ для контента Rentico.

- `digests/ГГГГ-ММ-ДД.md` — сводка за день. Новый файл в этой папке автоматически уходит в Telegram-бота (`.github/workflows/telegram.yml`).
- `archive/news.jsonl` — архив всех отобранных новостей, по одной на строку. По нему отсекаются дубли.
- `config/sources.md` — утверждённый список источников.
- `config/chat_id.txt` — ID чата в Telegram, определяется автоматически при первой отправке.

Секреты репозитория: `TELEGRAM_BOT_TOKEN` (обязательно), `TELEGRAM_CHAT_ID` (необязательно).
Повторно отправить сводку: Actions → Send digest to Telegram → Run workflow, указать путь к файлу.
