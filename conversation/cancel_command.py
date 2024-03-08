from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from conversation.messages import CANCEL_MESSAGE
from conversation.utils import log_info

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(CANCEL_MESSAGE, reply_markup=ReplyKeyboardRemove())
    await log_info(
        "{}: cancelled operation {}".format(
            update.effective_user.name, context.user_data["operation"]
        ),
        update.get_bot()
    )
    return ConversationHandler.END
