# EngyBot

EngyBot — Telegram-бот для изучения английского языка. Telegram используется как пользовательский интерфейс, а учебная логика, профиль пользователя, подбор контента, квизы, повторение и статистика работают на backend-стороне.

Демо-бот: `@engylernerbot`.

## Что реализовано

- регистрация через `/start` и сохранение учебного профиля;
- выбор родного языка интерфейса и уровня `A1-C2`;
- изучаемый язык: английский;
- раздел `Course` с юнитами, словарем, грамматикой и диалогами;
- 18 словарных тем и более 600 слов/фраз в seed-контенте;
- grammar units от `A1` до `C2`;
- диалоги с пошаговым чтением и заданиями на заполнение пропусков;
- короткие quiz-сессии с мгновенной обратной связью;
- форматы practice: choice, gap fill, definition, match;
- daily practice, закрепленная за текущей датой;
- review слабых слов и квиз по ошибкам;
- интервальное повторение через `mastery_level` и `review_due_at`;
- прогресс: попытки, точность, слабые слова, темы и цель дня;
- Docker Compose запуск с PostgreSQL;
- документация и финальная презентация для защиты.

## Учебная механика

Бот построен вокруг коротких учебных действий: открыть материал, выполнить небольшое задание, сразу получить обратную связь и вернуться к повторению позже. Такой подход близок к механикам Duolingo: короткие интерактивные уроки, персонализация сложности, активное вспоминание и регулярное повторение.

### Course

`Course` — основной учебный раздел.

- `Units` связывают словарь, grammar и диалоги в один тематический блок.
- `Vocabulary` показывает карточки слов и фраз с примерами.
- `Grammar` дает правило, паттерны и примеры по CEFR-уровням.
- `Dialogues` показывает мини-диалог по репликам, после чего открывает gap-fill задание.

Диалоговое задание сделано не как лекция и не как тест с кнопками. Пользователь видит фразу с пропуском:

```text
It comes in about _____ minutes.
```

Затем вводит ответ сообщением. Бот нормализует ввод, сверяет его с допустимыми вариантами и показывает правильный ответ с объяснением.

### Practice

`Practice` — активная тренировка.

- `Choice`: выбрать правильный перевод.
- `Gap fill`: восстановить пропущенное слово.
- `Definition`: угадать слово по определению.
- `Match`: сопоставить английскую фразу с русским значением.
- `Daily practice`: стабильный набор заданий на текущую дату.

После каждого ответа бот показывает feedback и обновляет персональный прогресс по слову.

### Review

`Review` использует реальные ошибки пользователя.

- слова с ошибками попадают в weak words;
- mistake quiz собирается из проблемных слов;
- после правильных ответов интервал повторения увеличивается;
- после ошибок слово возвращается быстрее.

### Progress

`Progress` показывает:

- количество завершенных попыток;
- общую точность;
- количество слабых слов;
- сколько слов пора повторить сегодня;
- прогресс по темам;
- дневную цель.

## Пользовательский сценарий

```text
/start
  -> профиль найден?
     -> нет:
        -> выбрать родной язык
        -> изучаемый язык: English
        -> выбрать уровень
        -> сохранить профиль
        -> главное меню
     -> да:
        -> главное меню

Главное меню
  -> Course
     -> Units
     -> Vocabulary
     -> Grammar
     -> Dialogues
  -> Practice
     -> Daily practice
     -> Mixed quiz
  -> Review
     -> Weak words
     -> Mistake quiz
  -> Profile
  -> Progress
  -> Help
```

## Стек

- `Python 3.12`
- `aiogram 3`
- `SQLAlchemy 2`
- `PostgreSQL 16`
- `Docker Compose`

SQLite и локальная MySQL не используются. Для разработки и демонстрации нужен PostgreSQL: через Docker Compose или локально.

## Структура проекта

```text
.
├── data/
│   └── seed/
│       ├── course_units.json
│       ├── dialogues.json
│       ├── grammar_units.json
│       └── word_sets.json
├── docs/
│   ├── architecture.md
│   ├── backlog.md
│   ├── case-compliance.md
│   ├── database.md
│   ├── final-presentation-outline.md
│   ├── project-overview.md
│   ├── team-roles.md
│   └── user-flow.md
├── src/
│   └── bot/
│       ├── database/
│       ├── handlers/
│       ├── keyboards/
│       ├── services/
│       ├── states/
│       ├── config.py
│       └── main.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Быстрый запуск

1. Создать `.env`:

```bash
cp .env.example .env
```

2. Указать токен Telegram-бота:

```env
BOT_TOKEN=123456:ABC...
```

3. Запустить приложение и PostgreSQL:

```bash
docker compose up --build -d
```

4. Проверить контейнеры:

```bash
docker compose ps
```

5. Посмотреть логи бота:

```bash
docker compose logs -f bot
```

## Переменные окружения

| Переменная | Назначение | Пример |
| --- | --- | --- |
| `BOT_TOKEN` | токен Telegram-бота из BotFather | `123456:ABC...` |
| `DATABASE_URL` | строка подключения SQLAlchemy к PostgreSQL | `postgresql+asyncpg://engybot:engybot@db:5432/engybot` |
| `DEFAULT_SOURCE_LANGUAGE` | родной язык по умолчанию | `ru` |
| `DEFAULT_TARGET_LANGUAGE` | изучаемый язык по умолчанию | `en` |

В Docker Compose приложение подключается к базе по хосту `db`. При локальном запуске без Docker укажите локальный PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://engybot:engybot@localhost:5432/engybot
```

## Локальный запуск без Docker для приложения

База все равно должна быть PostgreSQL.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m bot
```

## База данных

Схема создается автоматически при запуске через SQLAlchemy. Seed словаря синхронизируется при старте приложения.

Основные таблицы:

- `users` — Telegram-профиль, родной язык, изучаемый язык, уровень и bilingual UI;
- `word_sets` — словарные темы;
- `words` — слова и фразы внутри тем;
- `training_attempts` — завершенные quiz-сессии и результат;
- `user_word_progress` — персональный прогресс по словам, ошибки, mastery level и срок следующего review;
- `daily_practices` — стабильная практика дня по пользователю и дате.

Seed-контент хранится в `data/seed/`. `word_sets.json` загружается в БД, а `course_units.json`, `grammar_units.json` и `dialogues.json` читаются как JSON-источники для раздела `Course`.

## Очистка пользователей для повторной проверки регистрации

Если нужно заново пройти `/start` и onboarding, можно удалить пользовательские данные, не трогая учебный контент:

```bash
docker compose exec db psql -U engybot -d engybot -c "TRUNCATE users, training_attempts, user_word_progress, daily_practices RESTART IDENTITY CASCADE;"
```

После этого `word_sets` и `words` остаются в базе, а пользователи и их прогресс очищаются.

## Проверка проекта

```bash
python -m compileall src
jq empty data/seed/*.json
docker compose config --no-interpolate
```

Если используется виртуальное окружение:

```bash
PYTHONPATH=src .venv/bin/python -m compileall src
```

## Документация

- [Обзор проекта](docs/project-overview.md)
- [Архитектура](docs/architecture.md)
- [База данных](docs/database.md)
- [Сценарии пользователя](docs/user-flow.md)
- [Соответствие кейсу](docs/case-compliance.md)
- [Backlog](docs/backlog.md)
- [Роли в команде](docs/team-roles.md)

## Материалы для защиты

- [Финальная презентация](docs/EngyBot_final_presentation.pptx)
- [План презентации](docs/final-presentation-outline.md)
- [Матрица соответствия кейсу](docs/case-compliance.md)

Для живой демонстрации нужен запущенный бот с реальным `BOT_TOKEN`. Текущий demo username: `@engylernerbot`.

## Ограничения текущей версии

- прогресс по отдельным course units пока не хранится;
- grammar units пока являются учебным материалом, а не отдельным grammar-тренажером;
- часть bilingual UI еще можно выровнять по всем экранам;
- диалоги покрывают уровни `A1-B1`, для `B2-C2` есть словарь и grammar, но нужно больше dialogue-сценариев.

## Команда

| Участник | Группа | Зона ответственности |
| --- | --- | --- |
| Ширшов Даниил Константинович | М8О-308Б-23 | backend, архитектура, база данных, инфраструктура, логика бота |
| Фомин Владислав Николаевич | М8О-308Б-23 | контент, UX-сценарии, учебная логика, тестирование |
