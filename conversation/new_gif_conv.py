from dotenv import load_dotenv
import os
import emoji
import requests
from io import BytesIO
import re

load_dotenv()

from warnings import filterwarnings
from telegram import Update, InputSticker
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext,
)
from telegram.constants import StickerFormat
from telegram.warnings import PTBUserWarning

from processing.image import process_image
from processing.video import VideoProcessor
from conversation.messages import (
    UPLOAD_VIDEO,
    INVALID_VIDEO,
    VIDEO_SIZE_LIMIT_REACHED_MESSAGE,
    VIDEO_NAME_MESSAGE,
    VIDEO_SUCCESS_MESSAGE,
)
from conversation.utils import crop_button, done_button, emoji_button, log_info, no_crop_button, three_by_one_button, type_button

(
    SELECTING_VIDEO,
    SELECTING_NAME,

) = map(chr, range(2))
from conversation.cancel_command import cancel

MAX_STATIC_STICKER = 120
MAX_VIDEO_STICKER = 50
MAX_FILE_SIZE = 50000000  # 50mb


async def new_gif(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await log_info("{}: new gif".format(update.effective_user.name), update.get_bot())

    await update.message.reply_text(UPLOAD_VIDEO)
    return SELECTING_VIDEO

async def select_video_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remove_bg = False
    if update.message.video:
        # user sent a video
        file = await update.message.video.get_file()
    elif update.message.document and update.message.document.mime_type.startswith(
        "video"
    ):
        # user sent a file
        file = await update.message.document.get_file()
    elif update.message.video_note:
        # user sent a tele bubble
        file = await update.message.video_note.get_file()
        remove_bg = True
    else:
        await update.message.reply_text(INVALID_VIDEO)
        return SELECTING_VIDEO
    await log_info(
        "{}: uploaded video sticker {}".format(
            update.effective_user.name, file.file_id
        ),
        update.get_bot()
    )
    if file.file_size > MAX_FILE_SIZE:
        await log_info(
            "{}: file size limit reached {}".format(
                update.effective_user.name, file.file_size
            ),
            update.get_bot()
        )
        await update.message.reply_text(VIDEO_SIZE_LIMIT_REACHED_MESSAGE)
        return SELECTING_VIDEO
    processor = VideoProcessor(file, remove_bg=remove_bg)
    context.user_data["processor"] = processor
    await processor.get_video()
    await update.message.reply_text(VIDEO_NAME_MESSAGE)
    return SELECTING_NAME

async def select_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pack_name = update.message.text
    processor = context.user_data["processor"]
    response = update.message
    await log_info(
        "{}: selected sticker pack name".format(update.effective_user.name),
        update.get_bot()
    )
    # it is required to append the stickerbot name in a stickerpack created by a bot
    name = pack_name + "_by_" + os.environ.get("BOT_NAME")
    bot = update.get_bot()
    try:
        await response.reply_text(VIDEO_SUCCESS_MESSAGE.format(name))
        await log_info(
            "{}: created sticker pack".format(update.effective_user.name),
            update.get_bot()
        )
        return ConversationHandler.END
    except TelegramError as te:
        await response.reply_text(VIDEO_NAME_MESSAGE)
        await log_info(
            "{}: error creating pack {}".format(update.effective_user.name, te.message),
            update.get_bot()
        )
        return SELECTING_NAME


def get_new_gif_conv():
    filterwarnings(
        action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
    )
    return ConversationHandler(
        entry_points=[CommandHandler("newgif", new_gif)],
        states={
            SELECTING_VIDEO: [
                MessageHandler(filters.ALL & ~filters.COMMAND, select_video_sticker)
            ],
            SELECTING_NAME: [
                MessageHandler(filters.ALL & ~filters.COMMAND, select_name)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
