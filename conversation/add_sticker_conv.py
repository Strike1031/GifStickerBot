from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.constants import StickerFormat
import os

from conversation.new_pack_conv import (
    SELECTING_STICKER,
    SELECTING_DURATION,
    SELECTING_EMOJI,
    select_sticker,
    select_duration,
    select_emoji,
)
from conversation.messages import (
    IMAGE_STICKER_MESSAGE,
    VIDEO_STICKER_MESSAGE,
    STICKER_FROM_PACK_MESSAGE,
    ADD_SUCCESS_MESSAGE,
    INVALID_PACK_MESSAGE,
    UNHANDLED_ERROR_MESSAGE,
)
from conversation.utils import log_info
from conversation.cancel_command import cancel

SELECTING_PACK = map(chr, range(7, 8))


async def new_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await log_info("{}: add sticker".format(update.effective_user.name), update.get_bot())
    context.user_data["final_state"] = lambda u, c: add_sticker(u, c)
    context.user_data["stickers"] = list()
    context.user_data["operation"] = "add sticker"
    await update.message.reply_text(STICKER_FROM_PACK_MESSAGE)
    return SELECTING_PACK


async def select_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_name = update.message.sticker.set_name
    await log_info(
        "{}: selected sticker pack".format(update.effective_user.name),
        update.get_bot()
    )
    if not set_name.endswith("_by_" + os.environ.get("BOT_NAME")):
        await update.message.reply_text(INVALID_PACK_MESSAGE)
        await update.message.reply_text(STICKER_FROM_PACK_MESSAGE)
        return SELECTING_PACK
    bot = update.get_bot()
    sticker_set = await bot.get_sticker_set(set_name)
    context.user_data["set_name"] = set_name
    context.user_data["sticker_count"] = len(sticker_set.stickers)
    if sticker_set.is_video:
        context.user_data["type"] = StickerFormat.VIDEO
        await update.message.reply_text(VIDEO_STICKER_MESSAGE)
    else:
        context.user_data["type"] = StickerFormat.STATIC
        await update.message.reply_text(IMAGE_STICKER_MESSAGE)
    return SELECTING_STICKER


async def add_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = update.get_bot()
    try:
        for sticker in context.user_data["stickers"]:
            await bot.add_sticker_to_set(
                update.effective_user.id, context.user_data["set_name"], sticker=sticker
            )
        sticker_count = len(context.user_data["stickers"])
        await update.callback_query.message.reply_text(ADD_SUCCESS_MESSAGE.format(sticker_count))
        await log_info(
            "{}: added {} sticker(s)".format(update.effective_user.name, sticker_count),
            update.get_bot()
        )
    except TelegramError as te:
        await update.callback_query.message.reply_text(te.message)
        await update.callback_query.message.reply_text(UNHANDLED_ERROR_MESSAGE)
        await log_info(
            "{}: error adding sticker(s) {}".format(update.effective_user.name, te.message),
            update.get_bot()
        )
    return ConversationHandler.END


def get_add_sticker_conv():
    return ConversationHandler(
        entry_points=[CommandHandler("addsticker", new_sticker)],
        states={
            SELECTING_PACK: [
                MessageHandler(filters.Sticker.ALL & ~filters.COMMAND, select_pack)
            ],
            SELECTING_STICKER: [
                CallbackQueryHandler(select_sticker),
                MessageHandler(filters.ALL & ~filters.COMMAND, select_sticker)
            ],
            SELECTING_DURATION: [
                CallbackQueryHandler(select_duration),
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_duration)
            ],
            SELECTING_EMOJI: [
                CallbackQueryHandler(select_emoji),
                MessageHandler(filters.ALL & ~filters.COMMAND, select_emoji)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
