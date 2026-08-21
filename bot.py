import logging
import json
import os
import random
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════════════════════

TOKEN = "8946526999:AAFqRf5bT9Yd1-NHxIi82c5AohG3npF7dmQ"   # ← вставь токен от @BotFather
DATA_DIR = "data"           # папка с JSON-файлами пользователей

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  КОММЕНТАРИИ ПОСЛЕ ОТВЕТА  ← добавляй сюда свои фразы
# ═══════════════════════════════════════════════════════════════════════════════

CORRECT_REPLIES = [
    "Отлично! 🎉",
    "Верно, так держать! 💪",
    "Правильно! Ты молодец 🌟",
    "Супер! Продолжай в том же духе 🚀",
    "Именно! Отличная работа 👏",
    # добавляй сюда свои фразы ↑
]

WRONG_REPLIES = [
    "Не совсем, попробуй ещё раз 🤔",
    "Почти! Ещё одна попытка 💭",
    "Не угадала, попробуй снова 🙈",
    "Подумай ещё раз... 🤨",
    # добавляй сюда свои фразы ↑
]

# ═══════════════════════════════════════════════════════════════════════════════
#  КОНСТАНТЫ — состояния ConversationHandler
# ═══════════════════════════════════════════════════════════════════════════════

# Добавление слова
ADD_WORD, ADD_TRANSLATION, ADD_MORE_TRANSLATION, ADD_LEVEL, ADD_TOPIC, ADD_MORE_TOPIC = range(6)

# Редактирование слова
EDIT_WORD, EDIT_TRANSLATION, EDIT_MORE_TRANSLATION, EDIT_LEVEL, EDIT_TOPIC, EDIT_MORE_TOPIC = range(6, 12)

# Управление темами
TOPIC_MENU, TOPIC_NEW, TOPIC_RENAME_SELECT, TOPIC_RENAME_NEW, TOPIC_DELETE_SELECT, TOPIC_DELETE_CONFIRM = range(12, 18)

# Тренировка
TRAIN_DIRECTION, TRAIN_LIST, TRAIN_LEVEL_SELECT, TRAIN_TOPIC_SELECT, TRAIN_ANSWER = range(18, 23)

# Рестарт
RESTART_CONFIRM = 23

# Просмотр словаря
VIEW_MENU, VIEW_LEVEL_SELECT, VIEW_TOPIC_SELECT = range(24, 27)

CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# ═══════════════════════════════════════════════════════════════════════════════
#  РАБОТА С ДАННЫМИ
# ═══════════════════════════════════════════════════════════════════════════════

def user_file(user_id: int) -> str:
    return os.path.join(DATA_DIR, f"{user_id}.json")

def load_data(user_id: int) -> dict:
    path = user_file(user_id)
    if not os.path.exists(path):
        return {"words": {}, "topics": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(user_id: int, data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(user_file(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════════════════════════

def main_keyboard():
    return ReplyKeyboardMarkup([
        ["➕ Добавить слово",   "📋 Мой словарь"],
        ["✏️ Редактировать слово", "📂 Темы"],
        ["🎯 Тренировка",       "🔄 Рестарт"],
    ], resize_keyboard=True)

def level_keyboard(back=True, skip=True):
    row1 = ["A1", "A2", "B1"]
    row2 = ["B2", "C1", "C2"]
    extra = []
    if skip:
        extra.append("⏭ Пропустить")
    if back:
        extra.append("◀️ Назад")
    rows = [row1, row2]
    if extra:
        rows.append(extra)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def topics_keyboard(topics: list, back=True, skip=True, continue_btn=False):
    rows = [[t] for t in topics]
    extra = []
    if continue_btn:
        extra.append("✅ Продолжить")
    if skip:
        extra.append("⏭ Пропустить")
    if back:
        extra.append("◀️ Назад")
    if extra:
        rows.append(extra)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def yes_no_keyboard():
    return ReplyKeyboardMarkup([["✅ Обновить", "❌ Оставить старое"]], resize_keyboard=True)

def direction_keyboard():
    return ReplyKeyboardMarkup([
        ["🇷🇺→🇬🇧 RU → EN", "🇬🇧→🇷🇺 EN → RU"],
        ["◀️ Назад"],
    ], resize_keyboard=True)

def train_list_keyboard():
    return ReplyKeyboardMarkup([
        ["📚 Все слова", "⭐ Сложные слова"],
        ["📊 По уровню", "📂 По теме"],
        ["◀️ Назад"],
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

def back_cancel_keyboard():
    return ReplyKeyboardMarkup([["◀️ Назад", "❌ Отмена"]], resize_keyboard=True)

def continue_cancel_keyboard():
    return ReplyKeyboardMarkup([["✅ Продолжить", "❌ Отмена"]], resize_keyboard=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def format_word_card(word: str, info: dict) -> str:
    translations = ", ".join(info.get("translation", []))
    level = info.get("level") or "—"
    topics = ", ".join(info.get("topics", [])) or "—"
    errors = info.get("errors", 0)
    return (
        f"📝 *{word}*\n"
        f"Перевод: {translations}\n"
        f"Уровень: {level}\n"
        f"Темы: {topics}\n"
        f"Ошибок: {errors}"
    )

def check_answer(user_answer: str, correct_translations: list) -> bool:
    user_clean = user_answer.strip().lower()
    for t in correct_translations:
        if user_clean == t.strip().lower():
            return True
    return False

# ═══════════════════════════════════════════════════════════════════════════════
#  /start  и  главное меню
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! 👋 Я помогу тебе учить английскую лексику.\n\nВыбери действие:",
        reply_markup=main_keyboard(),
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Главное меню:", reply_markup=main_keyboard())

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК 1 — ДОБАВЛЕНИЕ СЛОВА
# ═══════════════════════════════════════════════════════════════════════════════

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add"] = {"translations": [], "topics": []}
    await update.message.reply_text(
        "✏️ Введи английское слово:",
        reply_markup=cancel_keyboard(),
    )
    return ADD_WORD

async def add_got_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)

    word = text.lower()
    uid = update.effective_user.id
    data = load_data(uid)

    if word in data["words"]:
        context.user_data["add"]["word"] = word
        context.user_data["add"]["existing"] = True
        info = data["words"][word]
        await update.message.reply_text(
            f"Слово *{word}* уже есть в словаре:\n\n{format_word_card(word, info)}\n\nЧто сделать?",
            parse_mode="Markdown",
            reply_markup=yes_no_keyboard(),
        )
        return ADD_WORD  # ждём ответа «обновить» / «оставить»

    context.user_data["add"]["word"] = word
    context.user_data["add"]["existing"] = False
    await update.message.reply_text(
        f"Слово: *{word}*\n\nВведи перевод (можно несколько — добавляй по одному):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return ADD_TRANSLATION

async def add_existing_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "✅ Обновить":
        word = context.user_data["add"]["word"]
        # переходим в режим редактирования
        context.user_data["edit"] = {"word": word, "translations": [], "topics": []}
        uid = update.effective_user.id
        data = load_data(uid)
        context.user_data["edit"]["old"] = data["words"][word].copy()
        await update.message.reply_text(
            f"Редактируем *{word}*. Введи новый перевод:",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return EDIT_TRANSLATION
    else:
        await update.message.reply_text("Оставляем слово без изменений.", reply_markup=main_keyboard())
        return ConversationHandler.END

async def add_got_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ Назад":
        await update.message.reply_text("Введи английское слово:", reply_markup=cancel_keyboard())
        return ADD_WORD

    context.user_data["add"]["translations"].append(text)
    await update.message.reply_text(
        f"Перевод *«{text}»* добавлен.\n\nДобавить ещё перевод или продолжить?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["✅ Продолжить", "◀️ Назад", "❌ Отмена"]], resize_keyboard=True),
    )
    return ADD_MORE_TRANSLATION

async def add_more_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ Назад":
        context.user_data["add"]["translations"].pop()
        await update.message.reply_text("Введи перевод:", reply_markup=cancel_keyboard())
        return ADD_TRANSLATION
    if text == "✅ Продолжить":
        await update.message.reply_text("Выбери уровень CEFR:", reply_markup=level_keyboard())
        return ADD_LEVEL
    # иначе — ещё один перевод
    context.user_data["add"]["translations"].append(text)
    await update.message.reply_text(
        f"Добавлено. Ещё перевод или продолжить?",
        reply_markup=ReplyKeyboardMarkup([["✅ Продолжить", "◀️ Назад", "❌ Отмена"]], resize_keyboard=True),
    )
    return ADD_MORE_TRANSLATION

async def add_got_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ Назад":
        await update.message.reply_text("Введи перевод:", reply_markup=cancel_keyboard())
        return ADD_TRANSLATION

    level = None if text == "⏭ Пропустить" else text
    if level and level not in CEFR_LEVELS:
        await update.message.reply_text("Выбери уровень кнопкой:", reply_markup=level_keyboard())
        return ADD_LEVEL

    context.user_data["add"]["level"] = level
    uid = update.effective_user.id
    data = load_data(uid)
    topics = data.get("topics", [])

    await update.message.reply_text(
        "Введи тему слова (или выбери из существующих):",
        reply_markup=topics_keyboard(topics, skip=True, back=True),
    )
    return ADD_TOPIC

async def add_got_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ Назад":
        await update.message.reply_text("Выбери уровень CEFR:", reply_markup=level_keyboard())
        return ADD_LEVEL
    if text == "⏭ Пропустить":
        return await _save_word(update, context, skip_topic=True)

    topic = text
    uid = update.effective_user.id
    data = load_data(uid)
    if topic not in data["topics"]:
        data["topics"].append(topic)
        save_data(uid, data)

    context.user_data["add"]["topics"].append(topic)
    await update.message.reply_text(
        f"Тема *«{topic}»* добавлена. Есть ещё тема? Напишите или нажмите «Продолжить»:",
        parse_mode="Markdown",
        reply_markup=topics_keyboard(data["topics"], skip=False, back=True, continue_btn=True),
    )
    return ADD_MORE_TOPIC

async def add_more_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ Назад":
        context.user_data["add"]["topics"] = context.user_data["add"]["topics"][:-1]
        uid = update.effective_user.id
        data = load_data(uid)
        await update.message.reply_text(
            "Введи тему:",
            reply_markup=topics_keyboard(data["topics"], skip=True, back=True),
        )
        return ADD_TOPIC
    if text == "✅ Продолжить":
        return await _save_word(update, context)

    uid = update.effective_user.id
    data = load_data(uid)
    topic = text
    if topic not in data["topics"]:
        data["topics"].append(topic)
        save_data(uid, data)

    context.user_data["add"]["topics"].append(topic)
    await update.message.reply_text(
        f"Тема *«{topic}»* добавлена. Ещё тема?",
        parse_mode="Markdown",
        reply_markup=topics_keyboard(data["topics"], skip=False, back=True, continue_btn=True),
    )
    return ADD_MORE_TOPIC

async def _save_word(update: Update, context: ContextTypes.DEFAULT_TYPE, skip_topic=False):
    uid = update.effective_user.id
    data = load_data(uid)
    add = context.user_data["add"]
    word = add["word"]

    data["words"][word] = {
        "translation": add["translations"],
        "level": add.get("level"),
        "topics": [] if skip_topic else add["topics"],
        "errors": 0,
    }
    save_data(uid, data)
    await update.message.reply_text(
        f"✅ Слово сохранено!\n\n{format_word_card(word, data['words'][word])}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК 2 — ПРОСМОТР СЛОВАРЯ
# ═══════════════════════════════════════════════════════════════════════════════

async def view_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Просмотр словаря — выбери фильтр:",
        reply_markup=ReplyKeyboardMarkup([
            ["📚 Все слова"],
            ["📊 По уровню", "📂 По теме"],
            ["◀️ Назад"],
        ], resize_keyboard=True),
    )
    return VIEW_MENU

async def view_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = load_data(uid)

    if text == "◀️ Назад" or text == "❌ Отмена":
        await update.message.reply_text("Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END

    if text == "📚 Все слова":
        words = data["words"]
        if not words:
            await update.message.reply_text("Словарь пуст. Добавь первое слово!", reply_markup=main_keyboard())
            return ConversationHandler.END
        lines = [f"• *{w}* — {', '.join(i['translation'])}" for w, i in sorted(words.items())]
        await update.message.reply_text("📚 *Все слова:*\n\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=main_keyboard())
        return ConversationHandler.END

    if text == "📊 По уровню":
        await update.message.reply_text("Выбери уровень:", reply_markup=level_keyboard(skip=False))
        return VIEW_LEVEL_SELECT

    if text == "📂 По теме":
        topics = data.get("topics", [])
        if not topics:
            await update.message.reply_text("Тем пока нет.", reply_markup=main_keyboard())
            return ConversationHandler.END
        await update.message.reply_text("Выбери тему:", reply_markup=topics_keyboard(topics, skip=False))
        return VIEW_TOPIC_SELECT

async def view_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "◀️ Назад":
        return await view_start(update, context)
    uid = update.effective_user.id
    data = load_data(uid)
    words = {w: i for w, i in data["words"].items() if i.get("level") == text}
    if not words:
        await update.message.reply_text(f"Слов уровня {text} нет.", reply_markup=main_keyboard())
    else:
        lines = [f"• *{w}* — {', '.join(i['translation'])}" for w, i in sorted(words.items())]
        await update.message.reply_text(f"📊 *Уровень {text}:*\n\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=main_keyboard())
    return ConversationHandler.END

async def view_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "◀️ Назад":
        return await view_start(update, context)
    uid = update.effective_user.id
    data = load_data(uid)
    words = {w: i for w, i in data["words"].items() if text in i.get("topics", [])}
    if not words:
        await update.message.reply_text(f"В теме «{text}» нет слов.", reply_markup=main_keyboard())
    else:
        lines = [f"• *{w}* — {', '.join(i['translation'])}" for w, i in sorted(words.items())]
        await update.message.reply_text(f"📂 *Тема «{text}»:*\n\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=main_keyboard())
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК 3 — РЕДАКТИРОВАНИЕ СЛОВА
# ═══════════════════════════════════════════════════════════════════════════════

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["edit"] = {"translations": [], "topics": []}
    await update.message.reply_text("Введи слово, которое хочешь редактировать:", reply_markup=cancel_keyboard())
    return EDIT_WORD

async def edit_got_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)

    word = text.lower()
    uid = update.effective_user.id
    data = load_data(uid)

    if word not in data["words"]:
        await update.message.reply_text(f"Слова *{word}* нет в словаре.", parse_mode="Markdown", reply_markup=cancel_keyboard())
        return EDIT_WORD

    context.user_data["edit"]["word"] = word
    context.user_data["edit"]["old"] = data["words"][word].copy()
    await update.message.reply_text(
        f"Текущие данные:\n\n{format_word_card(word, data['words'][word])}\n\nВведи новый перевод:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return EDIT_TRANSLATION

async def edit_got_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel_edit(update, context)
    context.user_data["edit"]["translations"].append(text)
    await update.message.reply_text(
        f"Добавлено. Ещё перевод или продолжить?",
        reply_markup=ReplyKeyboardMarkup([["✅ Продолжить", "◀️ Назад", "❌ Отмена"]], resize_keyboard=True),
    )
    return EDIT_MORE_TRANSLATION

async def edit_more_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel_edit(update, context)
    if text == "◀️ Назад":
        context.user_data["edit"]["translations"].pop()
        await update.message.reply_text("Введи перевод:", reply_markup=cancel_keyboard())
        return EDIT_TRANSLATION
    if text == "✅ Продолжить":
        await update.message.reply_text("Выбери уровень CEFR:", reply_markup=level_keyboard())
        return EDIT_LEVEL
    context.user_data["edit"]["translations"].append(text)
    await update.message.reply_text("Добавлено. Ещё?", reply_markup=ReplyKeyboardMarkup([["✅ Продолжить", "◀️ Назад", "❌ Отмена"]], resize_keyboard=True))
    return EDIT_MORE_TRANSLATION

async def edit_got_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel_edit(update, context)
    if text == "◀️ Назад":
        await update.message.reply_text("Введи перевод:", reply_markup=cancel_keyboard())
        return EDIT_TRANSLATION
    level = None if text == "⏭ Пропустить" else text
    context.user_data["edit"]["level"] = level
    uid = update.effective_user.id
    data = load_data(uid)
    await update.message.reply_text("Введи тему:", reply_markup=topics_keyboard(data["topics"], skip=True, back=True))
    return EDIT_TOPIC

async def edit_got_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel_edit(update, context)
    if text == "◀️ Назад":
        await update.message.reply_text("Выбери уровень:", reply_markup=level_keyboard())
        return EDIT_LEVEL
    if text == "⏭ Пропустить":
        return await _save_edit(update, context, skip_topic=True)

    uid = update.effective_user.id
    data = load_data(uid)
    if text not in data["topics"]:
        data["topics"].append(text)
        save_data(uid, data)
    context.user_data["edit"]["topics"].append(text)
    await update.message.reply_text(
        f"Тема *«{text}»* добавлена. Ещё?",
        parse_mode="Markdown",
        reply_markup=topics_keyboard(data["topics"], skip=False, back=True, continue_btn=True),
    )
    return EDIT_MORE_TOPIC

async def edit_more_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel_edit(update, context)
    if text == "◀️ Назад":
        context.user_data["edit"]["topics"] = context.user_data["edit"]["topics"][:-1]
        uid = update.effective_user.id
        data = load_data(uid)
        await update.message.reply_text("Введи тему:", reply_markup=topics_keyboard(data["topics"], skip=True, back=True))
        return EDIT_TOPIC
    if text == "✅ Продолжить":
        return await _save_edit(update, context)

    uid = update.effective_user.id
    data = load_data(uid)
    if text not in data["topics"]:
        data["topics"].append(text)
        save_data(uid, data)
    context.user_data["edit"]["topics"].append(text)
    await update.message.reply_text("Ещё тема?", reply_markup=topics_keyboard(data["topics"], skip=False, back=True, continue_btn=True))
    return EDIT_MORE_TOPIC

async def _save_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, skip_topic=False):
    uid = update.effective_user.id
    data = load_data(uid)
    edit = context.user_data["edit"]
    word = edit["word"]
    old_errors = edit["old"].get("errors", 0)

    data["words"][word] = {
        "translation": edit["translations"],
        "level": edit.get("level"),
        "topics": [] if skip_topic else edit["topics"],
        "errors": old_errors,
    }
    save_data(uid, data)
    await update.message.reply_text(
        f"✅ Слово обновлено!\n\n{format_word_card(word, data['words'][word])}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )
    return ConversationHandler.END

async def _cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    edit = context.user_data.get("edit", {})
    word = edit.get("word")
    if word:
        uid = update.effective_user.id
        data = load_data(uid)
        if word in data["words"] and "old" in edit:
            data["words"][word] = edit["old"]
            save_data(uid, data)
    await update.message.reply_text("Изменения отменены. Старые данные сохранены.", reply_markup=main_keyboard())
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК 4 — УПРАВЛЕНИЕ ТЕМАМИ
# ═══════════════════════════════════════════════════════════════════════════════

async def topics_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Управление темами:",
        reply_markup=ReplyKeyboardMarkup([
            ["📋 Список тем", "➕ Новая тема"],
            ["✏️ Переименовать", "🗑 Удалить тему"],
            ["◀️ Назад"],
        ], resize_keyboard=True),
    )
    return TOPIC_MENU

async def topics_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = load_data(uid)
    topics = data.get("topics", [])

    if text == "◀️ Назад":
        await update.message.reply_text("Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END

    if text == "📋 Список тем":
        if not topics:
            await update.message.reply_text("Тем пока нет.", reply_markup=main_keyboard())
            return ConversationHandler.END
        await update.message.reply_text("📂 Твои темы:\n\n" + "\n".join(f"• {t}" for t in topics), reply_markup=main_keyboard())
        return ConversationHandler.END

    if text == "➕ Новая тема":
        await update.message.reply_text("Введи название новой темы:", reply_markup=back_cancel_keyboard())
        return TOPIC_NEW

    if text == "✏️ Переименовать":
        if not topics:
            await update.message.reply_text("Тем нет.", reply_markup=main_keyboard())
            return ConversationHandler.END
        await update.message.reply_text("Выбери тему для переименования:", reply_markup=topics_keyboard(topics, skip=False))
        return TOPIC_RENAME_SELECT

    if text == "🗑 Удалить тему":
        if not topics:
            await update.message.reply_text("Тем нет.", reply_markup=main_keyboard())
            return ConversationHandler.END
        await update.message.reply_text("Выбери тему для удаления:", reply_markup=topics_keyboard(topics, skip=False))
        return TOPIC_DELETE_SELECT

async def topic_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ Назад":
        return await topics_start(update, context)
    uid = update.effective_user.id
    data = load_data(uid)
    if text in data["topics"]:
        await update.message.reply_text(f"Тема *«{text}»* уже существует.", parse_mode="Markdown", reply_markup=main_keyboard())
    else:
        data["topics"].append(text)
        save_data(uid, data)
        await update.message.reply_text(f"✅ Тема *«{text}»* создана.", parse_mode="Markdown", reply_markup=main_keyboard())
    return ConversationHandler.END

async def topic_rename_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "◀️ Назад":
        return await topics_start(update, context)
    context.user_data["rename_topic"] = text
    await update.message.reply_text(f"Введи новое название для темы *«{text}»*:", parse_mode="Markdown", reply_markup=back_cancel_keyboard())
    return TOPIC_RENAME_NEW

async def topic_rename_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ Назад":
        return await topics_start(update, context)

    old_name = context.user_data["rename_topic"]
    uid = update.effective_user.id
    data = load_data(uid)

    data["topics"] = [text if t == old_name else t for t in data["topics"]]
    for word_info in data["words"].values():
        word_info["topics"] = [text if t == old_name else t for t in word_info.get("topics", [])]
    save_data(uid, data)

    await update.message.reply_text(f"✅ Тема переименована: *«{old_name}»* → *«{text}»*", parse_mode="Markdown", reply_markup=main_keyboard())
    return ConversationHandler.END

async def topic_delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "◀️ Назад":
        return await topics_start(update, context)
    context.user_data["delete_topic"] = text
    await update.message.reply_text(
        f"⚠️ Вы точно хотите удалить тему *«{text}»*?\n\n"
        f"Все слова останутся в словаре, но потеряют эту тему. Это невозможно отменить.\n\n"
        f"Отправьте *подтверждаю* для удаления:",
        parse_mode="Markdown",
        reply_markup=back_cancel_keyboard(),
    )
    return TOPIC_DELETE_CONFIRM

async def topic_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text == "❌ отмена" or text == "❌ Отмена":
        return await _cancel(update, context)
    if text == "◀️ назад" or text == "◀️ Назад":
        return await topics_start(update, context)
    if text == "подтверждаю":
        topic = context.user_data["delete_topic"]
        uid = update.effective_user.id
        data = load_data(uid)
        data["topics"] = [t for t in data["topics"] if t != topic]
        for word_info in data["words"].values():
            word_info["topics"] = [t for t in word_info.get("topics", []) if t != topic]
        save_data(uid, data)
        await update.message.reply_text(f"🗑 Тема *«{topic}»* удалена.", parse_mode="Markdown", reply_markup=main_keyboard())
        return ConversationHandler.END
    await update.message.reply_text("Напиши *подтверждаю* для удаления или нажми «Назад»:", parse_mode="Markdown")
    return TOPIC_DELETE_CONFIRM

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК 5 — ТРЕНИРОВКА
# ═══════════════════════════════════════════════════════════════════════════════

async def train_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["train"] = {"attempts": 0}
    await update.message.reply_text("Выбери направление тренировки:", reply_markup=direction_keyboard())
    return TRAIN_DIRECTION

async def train_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "◀️ Назад":
        await update.message.reply_text("Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    if "RU" in text and "EN" in text:
        context.user_data["train"]["direction"] = "ru_en" if text.startswith("🇷🇺") else "en_ru"
    else:
        await update.message.reply_text("Выбери кнопкой:", reply_markup=direction_keyboard())
        return TRAIN_DIRECTION
    await update.message.reply_text("Выбери список для тренировки:", reply_markup=train_list_keyboard())
    return TRAIN_LIST

async def train_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = load_data(uid)

    if text == "◀️ Назад":
        await update.message.reply_text("Выбери направление:", reply_markup=direction_keyboard())
        return TRAIN_DIRECTION

    if text == "📚 Все слова":
        words = data["words"]
        return await _start_training(update, context, words)

    if text == "⭐ Сложные слова":
        words = {w: i for w, i in data["words"].items() if i.get("errors", 0) > 0}
        return await _start_training(update, context, words)

    if text == "📊 По уровню":
        await update.message.reply_text("Выбери уровень:", reply_markup=level_keyboard(skip=False))
        return TRAIN_LEVEL_SELECT

    if text == "📂 По теме":
        topics = data.get("topics", [])
        if not topics:
            await update.message.reply_text("Тем нет.", reply_markup=main_keyboard())
            return ConversationHandler.END
        await update.message.reply_text("Выбери тему:", reply_markup=topics_keyboard(topics, skip=False))
        return TRAIN_TOPIC_SELECT

async def train_level_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "◀️ Назад":
        await update.message.reply_text("Выбери список:", reply_markup=train_list_keyboard())
        return TRAIN_LIST
    uid = update.effective_user.id
    data = load_data(uid)
    words = {w: i for w, i in data["words"].items() if i.get("level") == text}
    return await _start_training(update, context, words, label=f"уровень {text}")

async def train_topic_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "◀️ Назад":
        await update.message.reply_text("Выбери список:", reply_markup=train_list_keyboard())
        return TRAIN_LIST
    uid = update.effective_user.id
    data = load_data(uid)
    words = {w: i for w, i in data["words"].items() if text in i.get("topics", [])}
    return await _start_training(update, context, words, label=f"тема «{text}»")

async def _start_training(update, context, words: dict, label=""):
    if not words:
        msg = f"В списке «{label}» нет слов." if label else "Словарь пуст."
        await update.message.reply_text(
            f"😔 {msg}\nВнеси слова сначала!",
            reply_markup=main_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["train"]["pool"] = list(words.keys())
    context.user_data["train"]["words"] = words
    context.user_data["train"]["attempts"] = 0
    return await _ask_word(update, context)

async def _ask_word(update, context):
    pool = context.user_data["train"]["pool"]
    words = context.user_data["train"]["words"]
    direction = context.user_data["train"]["direction"]

    word = random.choice(pool)
    context.user_data["train"]["current"] = word
    context.user_data["train"]["attempts"] = 0

    if direction == "ru_en":
        translations = words[word]["translation"]
        question = random.choice(translations)
        prompt = f"🇷🇺 *{question}*\n\nНапиши по-английски:"
    else:
        prompt = f"🇬🇧 *{word}*\n\nНапиши перевод:"

    await update.message.reply_text(
        prompt,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["🏁 Закончить тренировку"]], resize_keyboard=True),
    )
    return TRAIN_ANSWER

async def train_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id

    if text == "🏁 Закончить тренировку":
        await update.message.reply_text("Тренировка завершена! 💪 Так держать!", reply_markup=main_keyboard())
        return ConversationHandler.END

    train = context.user_data["train"]
    word = train["current"]
    words = train["words"]
    direction = train["direction"]
    attempts = train.get("attempts", 0)

    if direction == "ru_en":
        correct = [word]  # английское слово
    else:
        correct = words[word]["translation"]  # русские переводы

    if check_answer(text, correct):
        data = load_data(uid)
        if word in data["words"]:
            data["words"][word]["errors"] = max(0, data["words"][word].get("errors", 0) - 1)
            save_data(uid, data)
        reply = random.choice(CORRECT_REPLIES)
        await update.message.reply_text(reply, reply_markup=ReplyKeyboardMarkup([["🏁 Закончить тренировку"]], resize_keyboard=True))
        return await _ask_word(update, context)
    else:
        attempts += 1
        context.user_data["train"]["attempts"] = attempts

        if attempts < 3:
            reply = random.choice(WRONG_REPLIES)
            await update.message.reply_text(
                f"{reply} (Попытка {attempts}/3)",
                reply_markup=ReplyKeyboardMarkup([["🏁 Закончить тренировку"]], resize_keyboard=True),
            )
            return TRAIN_ANSWER
        else:
            data = load_data(uid)
            if word in data["words"]:
                data["words"][word]["errors"] = data["words"][word].get("errors", 0) + 1
                save_data(uid, data)
            correct_str = ", ".join(correct)
            await update.message.reply_text(
                f"❌ Все попытки исчерпаны.\nПравильный ответ: *{correct_str}*",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([["🏁 Закончить тренировку"]], resize_keyboard=True),
            )
            return await _ask_word(update, context)

# ═══════════════════════════════════════════════════════════════════════════════
#  БЛОК 7 — РЕСТАРТ
# ═══════════════════════════════════════════════════════════════════════════════

async def restart_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ *Внимание!*\n\nЭто удалит *все* твои слова и темы. Восстановить невозможно.\n\n"
        "Отправь *подтверждаю* для полного сброса:",
        parse_mode="Markdown",
        reply_markup=back_cancel_keyboard(),
    )
    return RESTART_CONFIRM

async def restart_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text == "подтверждаю":
        uid = update.effective_user.id
        save_data(uid, {"words": {}, "topics": []})
        await update.message.reply_text("✅ Аккаунт сброшен. Начинаем с чистого листа!", reply_markup=main_keyboard())
        return ConversationHandler.END
    if "отмена" in text or "назад" in text:
        return await _cancel(update, context)
    await update.message.reply_text("Напиши *подтверждаю* для сброса:", parse_mode="Markdown")
    return RESTART_CONFIRM

# ═══════════════════════════════════════════════════════════════════════════════
#  ОТМЕНА (общая)
# ═══════════════════════════════════════════════════════════════════════════════

async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=main_keyboard())
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _cancel(update, context)

# ═══════════════════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # ── Добавление слова ──────────────────────────────────────────────────────
    add_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить слово$"), add_start)],
        states={
            ADD_WORD:            [MessageHandler(filters.TEXT & ~filters.COMMAND, add_got_word),
                                  MessageHandler(filters.Regex("^(✅ Обновить|❌ Оставить старое)$"), add_existing_choice)],
            ADD_TRANSLATION:     [MessageHandler(filters.TEXT & ~filters.COMMAND, add_got_translation)],
            ADD_MORE_TRANSLATION:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_more_translation)],
            ADD_LEVEL:           [MessageHandler(filters.TEXT & ~filters.COMMAND, add_got_level)],
            ADD_TOPIC:           [MessageHandler(filters.TEXT & ~filters.COMMAND, add_got_topic)],
            ADD_MORE_TOPIC:      [MessageHandler(filters.TEXT & ~filters.COMMAND, add_more_topic)],
            EDIT_TRANSLATION:    [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_got_translation)],
            EDIT_MORE_TRANSLATION:[MessageHandler(filters.TEXT & ~filters.COMMAND, edit_more_translation)],
            EDIT_LEVEL:          [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_got_level)],
            EDIT_TOPIC:          [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_got_topic)],
            EDIT_MORE_TOPIC:     [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_more_topic)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command),
                   MessageHandler(filters.Regex("^❌ Отмена$"), _cancel)],
        allow_reentry=True,
    )

    # ── Просмотр словаря ──────────────────────────────────────────────────────
    view_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Мой словарь$"), view_start)],
        states={
            VIEW_MENU:         [MessageHandler(filters.TEXT & ~filters.COMMAND, view_menu_handler)],
            VIEW_LEVEL_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_level)],
            VIEW_TOPIC_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_topic)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command),
                   MessageHandler(filters.Regex("^❌ Отмена$"), _cancel)],
        allow_reentry=True,
    )

    # ── Редактирование слова ──────────────────────────────────────────────────
    edit_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Редактировать слово$"), edit_start)],
        states={
            EDIT_WORD:            [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_got_word)],
            EDIT_TRANSLATION:     [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_got_translation)],
            EDIT_MORE_TRANSLATION:[MessageHandler(filters.TEXT & ~filters.COMMAND, edit_more_translation)],
            EDIT_LEVEL:           [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_got_level)],
            EDIT_TOPIC:           [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_got_topic)],
            EDIT_MORE_TOPIC:      [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_more_topic)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command),
                   MessageHandler(filters.Regex("^❌ Отмена$"), _cancel)],
        allow_reentry=True,
    )

    # ── Темы ──────────────────────────────────────────────────────────────────
    topics_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📂 Темы$"), topics_start)],
        states={
            TOPIC_MENU:           [MessageHandler(filters.TEXT & ~filters.COMMAND, topics_menu_handler)],
            TOPIC_NEW:            [MessageHandler(filters.TEXT & ~filters.COMMAND, topic_new)],
            TOPIC_RENAME_SELECT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, topic_rename_select)],
            TOPIC_RENAME_NEW:     [MessageHandler(filters.TEXT & ~filters.COMMAND, topic_rename_new)],
            TOPIC_DELETE_SELECT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, topic_delete_select)],
            TOPIC_DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, topic_delete_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command),
                   MessageHandler(filters.Regex("^❌ Отмена$"), _cancel)],
        allow_reentry=True,
    )

    # ── Тренировка ────────────────────────────────────────────────────────────
    train_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎯 Тренировка$"), train_start)],
        states={
            TRAIN_DIRECTION:    [MessageHandler(filters.TEXT & ~filters.COMMAND, train_direction)],
            TRAIN_LIST:         [MessageHandler(filters.TEXT & ~filters.COMMAND, train_list_handler)],
            TRAIN_LEVEL_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, train_level_select)],
            TRAIN_TOPIC_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, train_topic_select)],
            TRAIN_ANSWER:       [MessageHandler(filters.TEXT & ~filters.COMMAND, train_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command),
                   MessageHandler(filters.Regex("^❌ Отмена$"), _cancel)],
        allow_reentry=True,
    )

    # ── Рестарт ───────────────────────────────────────────────────────────────
    restart_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔄 Рестарт$"), restart_start),
                      CommandHandler("restart", restart_start)],
        states={
            RESTART_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, restart_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command),
                   MessageHandler(filters.Regex("^❌ Отмена$"), _cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv)
    app.add_handler(view_conv)
    app.add_handler(edit_conv)
    app.add_handler(topics_conv)
    app.add_handler(train_conv)
    app.add_handler(restart_conv)

    print("✅ Бот запущен!")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await app.updater.idle()
        await app.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
