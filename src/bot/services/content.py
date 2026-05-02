import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import DailyPractice, TrainingAttempt, UserWordProgress, Word, WordSet


LEVEL_ORDER = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}

SEED_PATH = Path(__file__).resolve().parents[3] / "data" / "seed" / "word_sets.json"
GRAMMAR_SEED_PATH = Path(__file__).resolve().parents[3] / "data" / "seed" / "grammar_units.json"


QUIZ_FORMATS = {
    "choice": "Выбор правильного варианта",
    "gap": "Заполнение пропусков",
    "definition": "Угадай слово по определению",
    "match": "Соответствие",
}


WORD_DEFINITIONS = {
    "airplane": "Это средство передвижения по воздуху.",
    "salad": "Этот продукт часто используется для приготовления салата.",
    "manager": "Этот человек управляет командой на работе.",
    "sister": "Это ваш близкий родственник, который является дочерью ваших родителей.",
    "painting": "Это занятие, которое включает в себя создание изображений.",
    "passport": "Это документ, который позволяет вам путешествовать за границу.",
    "hotel": "Это место, где вы можете остановиться во время путешествия.",
    "chicken": "Это мясо, которое часто используется в салатах.",
    "coffee": "Какой напиток вы можете заказать в кафе?",
    "uncle": "Кто из ваших родственников — это брат вашей матери?",
    "music": "Какое хобби связано с музыкой?",
}


DIALOGUE_SCENARIOS = [
    {
        "id": "travel_checkin",
        "title": "Заселение в отель",
        "level": "A1",
        "theme": "Путешествия",
        "lines": [
            "Receptionist: Good evening. Do you have a reservation?",
            "Learner: Yes, I have a reservation for two nights.",
            "Receptionist: May I see your passport, please?",
            "Learner: Sure. Here is my passport.",
            "Receptionist: Thank you. Your room is on the third floor.",
        ],
    },
    {
        "id": "cafe_order",
        "title": "Заказ в кафе",
        "level": "A1",
        "theme": "Еда и напитки",
        "lines": [
            "Waiter: Are you ready to order?",
            "Learner: Yes. I would like a salad and a coffee.",
            "Waiter: Anything else?",
            "Learner: A glass of water, please.",
            "Waiter: Great. I will bring your order soon.",
        ],
    },
    {
        "id": "office_meeting",
        "title": "Обсуждение проекта",
        "level": "A2",
        "theme": "Работа и профессии",
        "lines": [
            "Manager: Let's discuss the project deadline.",
            "Learner: We need two more days to finish the presentation.",
            "Manager: What is the main issue right now?",
            "Learner: We are waiting for feedback from the client.",
            "Manager: Fine. Keep the team updated.",
        ],
    },
    {
        "id": "family_weekend",
        "title": "Планы на выходные с семьей",
        "level": "A2",
        "theme": "Семья и друзья",
        "lines": [
            "Friend: What are you doing this weekend?",
            "Learner: I am visiting my grandparents with my parents.",
            "Friend: That sounds nice. Are you staying there long?",
            "Learner: Just for one day, but we will have dinner together.",
            "Friend: Say hello to your family from me.",
        ],
    },
    {
        "id": "hobby_club",
        "title": "Разговор о хобби",
        "level": "B1",
        "theme": "Хобби и досуг",
        "lines": [
            "Club member: How did you get into photography?",
            "Learner: I started taking pictures during my travels.",
            "Club member: What do you enjoy most about it?",
            "Learner: I like capturing small details people usually miss.",
            "Club member: That is what makes the hobby rewarding.",
        ],
    },
    {
        "id": "media_discussion",
        "title": "Обсуждение статьи",
        "level": "B2",
        "theme": "Технологии и медиа",
        "lines": [
            "Colleague: Did you read the article about social media algorithms?",
            "Learner: Yes, and I found its main argument quite convincing.",
            "Colleague: What stood out to you the most?",
            "Learner: The way it explained the influence of headlines on public opinion.",
            "Colleague: I agree. It raised several important concerns.",
        ],
    },
]


def load_seed_word_sets() -> list[dict]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def load_grammar_units() -> list[dict]:
    return json.loads(GRAMMAR_SEED_PATH.read_text(encoding="utf-8"))


def level_is_allowed(user_level: str, content_level: str) -> bool:
    return LEVEL_ORDER.get(content_level, 999) <= LEVEL_ORDER.get(user_level, 999)


def filter_words_for_level(words: list[Word], user_level: str | None) -> list[Word]:
    if user_level is None:
        return list(words)
    return [word for word in words if level_is_allowed(user_level, word.level)]


def get_level_range(levels: list[str]) -> str:
    if not levels:
        return "A1"
    unique_levels = sorted(set(levels), key=lambda item: LEVEL_ORDER.get(item, 999))
    if len(unique_levels) == 1:
        return unique_levels[0]
    return f"{unique_levels[0]}-{unique_levels[-1]}"


def get_word_set_level_range(word_set: WordSet, user_level: str | None = None) -> str:
    words = filter_words_for_level(word_set.words, user_level)
    if not words:
        words = word_set.words
    return get_level_range([word.level for word in words])


def normalize_seed_payload(payloads: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for payload in sorted(payloads, key=lambda item: item["title"]):
        normalized.append(
            {
                "title": payload["title"],
                "description": payload["description"],
                "level": payload["level"],
                "words": sorted(
                    [
                        {
                            "source_text": word["source_text"],
                            "target_text": word["target_text"],
                            "level": word["level"],
                            "example": word["example"],
                        }
                        for word in payload["words"]
                    ],
                    key=lambda item: (item["level"], item["source_text"], item["target_text"]),
                ),
            }
        )
    return normalized


def normalize_db_payload(word_sets: list[WordSet]) -> list[dict]:
    normalized: list[dict] = []
    for word_set in sorted(word_sets, key=lambda item: item.title):
        normalized.append(
            {
                "title": word_set.title,
                "description": word_set.description,
                "level": word_set.level,
                "words": sorted(
                    [
                        {
                            "source_text": word.source_text,
                            "target_text": word.target_text,
                            "level": word.level,
                            "example": word.example,
                        }
                        for word in word_set.words
                    ],
                    key=lambda item: (item["level"], item["source_text"], item["target_text"]),
                ),
            }
        )
    return normalized


async def seed_word_sets(session: AsyncSession) -> None:
    payloads = load_seed_word_sets()
    existing_result = await session.execute(select(WordSet).options(selectinload(WordSet.words)))
    existing_word_sets = list(existing_result.scalars().all())

    if normalize_db_payload(existing_word_sets) == normalize_seed_payload(payloads):
        return

    await session.execute(delete(DailyPractice))
    await session.execute(delete(UserWordProgress))
    await session.execute(delete(TrainingAttempt))
    await session.execute(delete(Word))
    await session.execute(delete(WordSet))
    await session.commit()

    for payload in payloads:
        word_set = WordSet(
            title=payload["title"],
            description=payload["description"],
            level=payload["level"],
            is_active=True,
        )
        for word in payload["words"]:
            word_set.words.append(
                Word(
                    source_text=word["source_text"],
                    target_text=word["target_text"],
                    level=word["level"],
                    example=word["example"],
                )
            )
        session.add(word_set)

    await session.commit()
