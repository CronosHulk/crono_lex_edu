from __future__ import annotations

PART_OF_SPEECH_LABELS = {
    "uk": {
        "noun": "іменник",
        "verb": "дієслово",
        "adjective": "прикметник",
        "adverb": "прислівник",
        "pronoun": "займенник",
        "preposition": "прийменник",
        "conjunction": "сполучник",
        "interjection": "вигук",
        "article": "артикль",
        "determiner": "визначник",
        "modal verb": "модальне дієслово",
        "auxiliary verb": "допоміжне дієслово",
        "phrasal verb": "фразове дієслово",
        "numeral": "числівник",
        "prefix": "префікс",
        "suffix": "суфікс",
        "abbreviation": "скорочення",
        "idiom": "ідіома",
    }
}

CATEGORY_LABELS = {
    "uk": {
        "actions": "дії",
        "activity": "активність",
        "addition": "додавання",
        "age": "вік",
        "animals": "тварини",
        "appearance": "зовнішність",
        "architecture": "архітектура",
        "art": "мистецтво",
        "arts": "мистецтва",
        "awards": "нагороди",
        "basic": "базове",
        "beauty": "краса",
        "behavior": "поведінка",
        "body": "тіло",
        "building": "будівництво",
        "business": "бізнес",
        "change": "зміни",
        "choice": "вибір",
        "city": "місто",
        "clothes": "одяг",
        "color": "колір",
        "colors": "кольори",
        "comms": "комунікації",
        "communication": "спілкування",
        "contrast": "контраст",
        "crime": "злочинність",
        "culture": "культура",
        "daily": "щоденне",
        "data": "дані",
        "death": "смерть",
        "degree": "ступінь",
        "direction": "напрям",
        "discovery": "відкриття",
        "distance": "відстань",
        "document": "документ",
        "drama": "драма",
        "dreams": "мрії",
        "ecology": "екологія",
        "education": "освіта",
        "emotions": "емоції",
        "energy": "енергія",
        "entertainment": "розваги",
        "ethics": "етика",
        "events": "події",
        "family": "сім'я",
        "fashion": "мода",
        "feelings": "почуття",
        "fiction": "художня література",
        "finance": "фінанси",
        "fire": "вогонь",
        "food": "їжа",
        "formal": "формальне",
        "frequency": "частотність",
        "furniture": "меблі",
        "games": "ігри",
        "gender": "гендер",
        "general": "загальне",
        "geography": "географія",
        "ghost": "привиди",
        "goal": "мета",
        "government": "уряд",
        "grammar": "граматика",
        "health": "здоров'я",
        "help": "допомога",
        "history": "історія",
        "hobby": "хобі",
        "holiday": "свято",
        "home": "дім",
        "house": "будинок",
        "household": "побут",
        "ideas": "ідеї",
        "identity": "ідентичність",
        "importance": "важливість",
        "industry": "індустрія",
        "informal": "неформальне",
        "insects": "комахи",
        "investigation": "розслідування",
        "it": "ІТ",
        "job": "робота",
        "law": "право",
        "leisure": "дозвілля",
        "life": "життя",
        "lifestyle": "спосіб життя",
        "light": "світло",
        "literary": "літературне",
        "literature": "література",
        "living": "проживання",
        "location": "місце",
        "logic": "логіка",
        "luck": "удача",
        "materials": "матеріали",
        "math": "математика",
        "media": "медіа",
        "medicine": "медицина",
        "military": "військова справа",
        "mind": "мислення",
        "money": "гроші",
        "more": "додаткове",
        "movement": "рух",
        "movie": "кіно",
        "music": "музика",
        "nature": "природа",
        "news": "новини",
        "numbers": "числа",
        "office": "офіс",
        "order": "порядок",
        "paper": "папір",
        "people": "люди",
        "personality": "особистість",
        "philosophy": "філософія",
        "physics": "фізика",
        "plan": "планування",
        "politics": "політика",
        "position": "позиція",
        "possession": "володіння",
        "power": "сила",
        "probability": "ймовірність",
        "problem": "проблеми",
        "progress": "прогрес",
        "psych": "психологія",
        "psychology": "психологія",
        "quality": "якість",
        "quantity": "кількість",
        "relation": "зв'язок",
        "relations": "стосунки",
        "religion": "релігія",
        "results": "результати",
        "road": "дорога",
        "rules": "правила",
        "safety": "безпека",
        "science": "наука",
        "security": "захист",
        "sequence": "послідовність",
        "shape": "форма",
        "shipping": "доставка",
        "shopping": "покупки",
        "size": "розмір",
        "skills": "навички",
        "social": "соціальне",
        "society": "суспільство",
        "sound": "звук",
        "sounds": "звуки",
        "sources": "джерела",
        "space": "простір",
        "speech": "мовлення",
        "sports": "спорт",
        "state": "стан",
        "study": "навчання",
        "success": "успіх",
        "tech": "технології",
        "technical": "технічне",
        "technology": "технології",
        "time": "час",
        "tools": "інструменти",
        "traffic": "рух транспорту",
        "transition": "перехід",
        "transport": "транспорт",
        "travel": "подорожі",
        "truth": "правда",
        "vision": "зір",
        "war": "війна",
        "weather": "погода",
        "work": "праця",
        "writing": "письмо",
        "common": "поширене",
    }
}

CATEGORY_LABELS["ru"] = {
    **CATEGORY_LABELS["uk"],
    "actions": "действия",
    "business": "бизнес",
    "communication": "общение",
    "crime": "преступность",
    "degree": "степень",
    "education": "образование",
    "emotion": "эмоции",
    "emotions": "эмоции",
    "job": "работа",
    "math": "математика",
    "nature": "природа",
    "planning": "планирование",
    "quality": "качество",
    "science": "наука",
    "travel": "путешествия",
    "work": "работа",
}

CATEGORY_LABELS["pl"] = {
    **CATEGORY_LABELS["uk"],
    "actions": "dzialania",
    "business": "biznes",
    "communication": "komunikacja",
    "crime": "przestepczosc",
    "degree": "stopien",
    "education": "edukacja",
    "emotion": "emocje",
    "emotions": "emocje",
    "job": "praca",
    "math": "matematyka",
    "nature": "natura",
    "planning": "planowanie",
    "quality": "jakosc",
    "science": "nauka",
    "travel": "podroze",
    "work": "praca",
}


def translate_part_of_speech_label(locale: str, part_of_speech: str | None) -> str | None:
    if not part_of_speech:
        return None
    normalized = " ".join(part_of_speech.strip().lower().split())
    translated = PART_OF_SPEECH_LABELS.get(locale, {}).get(normalized)
    if translated:
        return translated
    return part_of_speech.strip()


def format_part_of_speech_labels(locale: str, parts_of_speech: list[str] | None) -> str:
    if not parts_of_speech:
        return ""
    labels: list[str] = []
    for part_of_speech in parts_of_speech:
        label = translate_part_of_speech_label(locale, part_of_speech)
        if label and label not in labels:
            labels.append(label)
    return ", ".join(labels)


def translate_category_label(locale: str, category: str | None) -> str | None:
    if not category:
        return None
    normalized = " ".join(category.strip().lower().split())
    translated = CATEGORY_LABELS.get(locale, {}).get(normalized)
    if translated:
        return translated
    return category.strip()


def format_category_labels(locale: str, categories: list[str] | None) -> str:
    if not categories:
        return ""
    labels: list[str] = []
    for category in categories:
        label = translate_category_label(locale, category)
        if label and label not in labels:
            labels.append(label[:1].upper() + label[1:])
    return ", ".join(labels)
