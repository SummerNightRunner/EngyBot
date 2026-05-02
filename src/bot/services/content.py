import json
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import TrainingAttempt, Word, WordSet


LEVEL_ORDER = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}

SEED_PATH = Path(__file__).resolve().parents[3] / "data" / "seed" / "word_sets.json"


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


def level_is_allowed(user_level: str, content_level: str) -> bool:
    return LEVEL_ORDER.get(content_level, 999) <= LEVEL_ORDER.get(user_level, 999)


async def seed_word_sets(session: AsyncSession) -> None:
    payloads = load_seed_word_sets()

    titles_result = await session.execute(select(WordSet.title).order_by(WordSet.title))
    existing_titles = list(titles_result.scalars().all())
    expected_titles = sorted(item["title"] for item in payloads)

    word_count_result = await session.execute(select(func.count(Word.id)))
    existing_words_count = word_count_result.scalar_one()
    expected_words_count = sum(len(item["words"]) for item in payloads)

    if existing_titles == expected_titles and existing_words_count == expected_words_count:
        return

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
                    example=word["example"],
                )
            )
        session.add(word_set)

    await session.commit()
