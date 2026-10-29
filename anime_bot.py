import html
import logging
import os

import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Токен берём из переменной окружения BOT_TOKEN или вставляем сюда
TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")
API = "https://api.jikan.moe/v4"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("anime_bot")


async def api_get(path: str, params: dict | None = None) -> dict | None:
    """Запрос к Jikan API (бесплатный, без ключа)."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{API}{path}", params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        log.error("API error: %s", e)
        return None


def build_card(a: dict) -> tuple[str, str | None]:
    """Делает подпись и ссылку на постер для аниме."""
    title = html.escape(a.get("title") or "Без названия")
    score = a.get("score") or "—"
    episodes = a.get("episodes") or "?"
    year = a.get("year") or "—"
    status = html.escape(a.get("status") or "—")
    genres = ", ".join(g["name"] for g in a.get("genres", [])) or "—"
    synopsis = a.get("synopsis") or "Описания нет."
    if len(synopsis) > 450:
        synopsis = synopsis[:450].rsplit(" ", 1)[0] + "…"

    text = (
        f"<b>{title}</b>\n"
        f"⭐ {score} | 📺 Эпизодов: {episodes} | 📅 {year}\n"
        f"Статус: {status}\n"
        f"Жанры: {html.escape(genres)}\n\n"
        f"{html.escape(synopsis)}\n\n"
        f"<a href=\"{a.get('url', '')}\">MyAnimeList</a>"
    )
    image = (
        a.get("images", {}).get("jpg", {}).get("large_image_url")
        or a.get("images", {}).get("jpg", {}).get("image_url")
    )
    return text, image


async def send_card(update: Update, anime: dict) -> None:
    text, image = build_card(anime)
    if image:
        await update.message.reply_photo(
            photo=image, caption=text, parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ---------- Команды ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name if update.effective_user else "друг"
    await update.message.reply_text(
        f"Привет, {name}! 👋 Я аниме-бот.\n\n"
        "Что я умею:\n"
        "/random — случайное аниме\n"
        "/top — топ-10 аниме\n"
        "/search название — поиск аниме\n"
        "/help — помощь\n\n"
        "Или просто напиши название аниме."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/random — случайное аниме\n"
        "/top — топ-10 по рейтингу\n"
        "/search Naruto — поиск по названию"
    )


async def random_anime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = await api_get("/random/anime")
    if not data or "data" not in data:
        await update.message.reply_text("Не удалось получить аниме 😢 Попробуй ещё раз.")
        return
    await send_card(update, data["data"])


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = await api_get("/top/anime", {"limit": 10})
    if not data or not data.get("data"):
        await update.message.reply_text("Не удалось получить топ 😢")
        return
    lines = ["🏆 <b>Топ-10 аниме</b>\n"]
    for i, a in enumerate(data["data"], 1):
        lines.append(f"{i}. {html.escape(a['title'])} — ⭐ {a.get('score') or '—'}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def do_search(update: Update, query: str) -> None:
    data = await api_get("/anime", {"q": query, "limit": 1, "sfw": "true"})
    if not data or not data.get("data"):
        await update.message.reply_text("Ничего не нашёл 🤷 Попробуй название на английском.")
        return
    await send_card(update, data["data"][0])


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Напиши так: /search Naruto")
        return
    await do_search(update, query)


async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await do_search(update, update.message.text.strip())


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Ошибка: %s", context.error)


def main() -> None:
    if TOKEN == "ВСТАВЬ_ТОКЕН_СЮДА":
        raise SystemExit("Укажи токен бота от @BotFather!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("random", random_anime))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search))
    app.add_error_handler(on_error)

    log.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
  
