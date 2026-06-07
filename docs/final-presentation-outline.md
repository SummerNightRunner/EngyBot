# Финальная презентация EngyBot

## 1. EngyBot

Telegram-бот для изучения английского языка. MVP backend-first EdTech-продукта с Telegram как пользовательским интерфейсом.

Demo username: `@engylernerbot`.

## 2. Задача кейса

- регистрация пользователя через `/start`;
- настройка профиля: родной язык, изучаемый язык, уровень;
- изучение новых слов и фраз;
- проверка знаний через квизы;
- сохранение статистики и прогресса;
- техническая документация и запуск через Docker.

## 3. Продуктовая идея

EngyBot использует micro-learning: короткие учебные сессии, быстрые карточки, daily practice и повторение ошибок.

## 4. Пользовательский сценарий

`/start` -> onboarding -> главное меню -> Course / Practice / Review / Profile / Progress / Help.

## 5. Архитектура

Монолитный Telegram bot backend:

- `aiogram` обрабатывает команды и callback-запросы;
- handlers отвечают за сценарии;
- services загружают контент и формируют учебную логику;
- SQLAlchemy сохраняет пользователей, попытки и прогресс;
- PostgreSQL работает как постоянное хранилище.

## 6. База данных

Основные таблицы:

- `users`;
- `word_sets`;
- `words`;
- `training_attempts`;
- `user_word_progress`;
- `daily_practices`.

## 7. Course

- course units;
- vocabulary topics;
- grammar units A1-C2;
- dialogues from JSON seed;
- dialogue gap-fill tasks;
- bilingual UI.

## 8. Practice

- mixed quiz;
- choice, gap fill, definition, match;
- immediate feedback;
- daily practice with stable date-based set.

## 9. Review и Progress

- weak words from real mistakes;
- mistake quiz;
- spaced repetition with mastery level and next review date;
- total attempts;
- accuracy;
- topic progress;
- daily goal and streak.

## 10. Контент и вклад команды

- backend, БД, инфраструктура и логика бота;
- словарь, grammar units, course units и dialogues;
- тестирование пользовательских сценариев.

## 11. Стабилизация

- Docker Compose;
- `.env.example`;
- fallback для неверного текстового ввода;
- fallback для устаревших callback-кнопок;
- документация по запуску и БД.

## 12. Демо

1. `/start` и onboarding.
2. Открыть Course -> Units.
3. Показать карточку слова и grammar unit.
4. Открыть dialogue и заполнить пропуск.
5. Пройти quiz.
6. Показать Review и Progress.
