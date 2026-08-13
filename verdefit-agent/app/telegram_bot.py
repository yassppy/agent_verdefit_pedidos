import asyncio
import logging
import os

from agent import root_agent
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import ServerError
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("Falta TELEGRAM_BOT_TOKEN en el archivo .env")

session_service = InMemorySessionService()
APP_NAME = "verdefit_telegram"

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start en Telegram con un saludo natural."""
    if update.message is None:
        return

    mensaje_bienvenida = (
        "¡Hola! 🥗 Bienvenid@ a **VerdeFit**, tu espacio de comida saludable.\n\n"
        "Estoy aquí para ayudarte a elegir tu menú del día o registrar tu pedido. "
        "¿En qué te puedo ayudar hoy?"
    )

    await update.message.reply_text(
        mensaje_bienvenida,
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe los mensajes de Telegram y los envía al Runner del ADK con reintentos."""
    message = update.message
    if message is None or message.text is None:
        return

    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return

    user_message = message.text
    chat_id = str(chat.id)
    user_id = str(user.id)

    logger.info("Mensaje de %s (%s): %s", user_id, chat_id, user_message)

    await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=chat_id,
            )

            if session is None:
                await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=chat_id,
                )

            content = types.Content(
                role="user",
                parts=[types.Part(text=f"[Telegram ID: {chat_id}] {user_message}")],
            )

            final_response: str | None = None

            async for event in runner.run_async(
                user_id=user_id,
                session_id=chat_id,
                new_message=content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_response = part.text

            if final_response:
                await message.reply_text(final_response)
            else:
                await message.reply_text(
                    "No pude procesar la respuesta. ¿Podrías intentar de nuevo?"
                )
            break

        except ServerError as e:
            if e.code == 503 and attempt < max_retries - 1:
                logger.warning(
                    f"Servidor ocupado (503). Reintentando ({attempt + 1}/{max_retries})..."
                )
                await asyncio.sleep(2)
                continue
            logger.exception("Error de servidor no recuperable.")
            await message.reply_text(
                "El servidor está experimentando una alta demanda en este momento. Por favor, intenta de nuevo en unos segundos."
            )
            break
        except Exception:
            logger.exception("Error procesando mensaje")
            await message.reply_text(
                "Ocurrió un error al procesar tu solicitud. Por favor intenta más tarde."
            )
            break


def main() -> None:
    # Le indicamos explícitamente al analizador de tipos que la variable no es None
    assert TELEGRAM_TOKEN is not None, "TELEGRAM_BOT_TOKEN no está configurado"

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot de Telegram VerdeFit iniciado...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
