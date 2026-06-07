# Соответствие кейсу

Файл кейса: `03_Кейс_«Разработка_Telegram_бота_для_изучения_иностранных_языков».docx`.

## Обязательный MVP

| Требование кейса | Статус | Где реализовано |
| --- | --- | --- |
| Telegram-бот как основной интерфейс | выполнено | `src/bot/main.py`, `src/bot/handlers/` |
| `/start` и регистрация пользователя | выполнено | `src/bot/handlers/start.py` |
| Настройка профиля: язык, уровень | выполнено | onboarding/profile handlers, `users` |
| Изучение слов и фраз | выполнено | `Course -> Vocabulary`, `word_sets`, `words` |
| Карточки слов | выполнено | `learn:card`, `card_keyboard` |
| Проверка знаний через квизы | выполнено | `Practice -> Mixed Quiz` |
| Выбор правильного варианта | выполнено | `choice` quiz format |
| Дополнительные форматы квиза | выполнено | `gap`, `definition`, `match` |
| Личная статистика | выполнено | `Progress`, `training_attempts` |
| Прогресс по словам | выполнено | `user_word_progress` |
| Повторение ошибок | выполнено | `Review`, weak words, mistake quiz |
| Daily practice | выполнено | `daily_practices` |
| User Flow | выполнено | `docs/user-flow.md` |
| README с запуском | выполнено | `README.md` |
| Описание БД | выполнено | `README.md`, `docs/database.md` |
| Docker/контейнеризация | выполнено | `Dockerfile`, `docker-compose.yml` |
| Финальная презентация | выполнено | `docs/EngyBot_final_presentation.pptx` |

## Дополнительные улучшения

| Улучшение | Статус | Где реализовано |
| --- | --- | --- |
| Course units | выполнено | `data/seed/course_units.json`, `Course -> Units` |
| Grammar units A1-C2 | выполнено | `data/seed/grammar_units.json`, `Course -> Grammar` |
| Диалоги из seed-файла | выполнено | `data/seed/dialogues.json`, `load_dialogue_scenarios()` |
| Задания по диалогам | выполнено | gap-fill FSM: `dialogue:task`, `DialogueStates.awaiting_gap_answer`, `tasks` в `dialogues.json` |
| Bilingual UI | выполнено частично | профиль, меню, course/practice screens |
| Fallback на неверный текст | выполнено | `text_fallback_handler`, `quiz_text_fallback_handler` |
| Fallback на неизвестный callback | выполнено | `unknown_callback_handler` |
| Интервальное повторение | выполнено | `mastery_level`, `review_due_at`, Review |

## Что требует внешнего окружения

| Пункт | Комментарий |
| --- | --- |
| Ссылка на работающего бота / username | username: `@engylernerbot`; для живой демонстрации нужен запущенный процесс бота |
| Постоянный аптайм | решается деплоем Docker Compose на сервер |
| Живая демонстрация | требуется запущенный бот и Telegram-клиент |
| Интеграции переводчика/TTS | в кейсе указаны как возможные внешние API, для MVP не являются обязательными |

## Итог

Проект закрывает основную формулировку MVP из кейса: пользователь регистрируется, настраивает профиль, изучает контент, проходит квизы, получает обратную связь, видит статистику и может повторять ошибки. Для финальной сдачи остается только запустить бота с реальным токеном и указать username в презентации или README.
