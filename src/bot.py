import docker
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import asyncio
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MONITOR_INTERVAL = int(os.getenv('MONITOR_INTERVAL', '5'))

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("Missing Telegram bot token or chat ID")

# Docker client setup
docker_client = docker.from_env()
container_states = {}

def authorized(chat_id):
    return str(chat_id) == TELEGRAM_CHAT_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update.effective_chat.id):
        await update.message.reply_text("⛔ Unauthorized access")
        return
    await update.message.reply_text(
        "🐳 Docker Monitor Bot Active\n\n"
        "Commands:\n"
        "/list - Show running containers\n"
        "/help - Show this message"
    )

async def list_containers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update.effective_chat.id):
        return
    
    try:
        containers = docker_client.containers.list()
        if not containers:
            await update.message.reply_text("No containers running")
            return
            
        message = ["🏃 Running Containers:"]
        for container in containers:
            status = container.status
            health = container.attrs.get('State', {}).get('Health', {}).get('Status')
            message.append(
                f"• {container.name} ({container.short_id}) - {status}"
                f"{f' ({health})' if health else ''}"
            )
        await update.message.reply_text("\n".join(message))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def check_containers(context: ContextTypes.DEFAULT_TYPE):
    while True:
        try:
            current_containers = {
                c.id: {
                    'name': c.name,
                    'status': c.status,
                    'health': c.attrs.get('State', {}).get('Health', {}).get('Status')
                }
                for c in docker_client.containers.list(all=True)
            }

            # Check for changes
            for cid, current in current_containers.items():
                if cid in container_states:
                    previous = container_states[cid]
                    
                    if current['status'] != previous['status']:
                        await notify(context.bot, 
                            f"🔄 Status Change: {current['name']}\n"
                            f"{previous['status']} → {current['status']}"
                        )
                    
                    if (current['health'] and previous['health'] and 
                        current['health'] != previous['health']):
                        await notify(context.bot,
                            f"🩺 Health Change: {current['name']}\n"
                            f"{previous['health']} → {current['health']}"
                        )
                else:
                    await notify(context.bot,
                        f"🆕 New Container: {current['name']}\n"
                        f"Status: {current['status']}"
                    )

            for cid in set(container_states) - set(current_containers):
                await notify(context.bot, f"🗑️ Removed: {container_states[cid]['name']}")

            container_states.clear()
            container_states.update(current_containers)
            
            await asyncio.sleep(MONITOR_INTERVAL)
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
            await asyncio.sleep(30)

async def notify(bot, message: str):
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n{message}"
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_containers))
    application.add_handler(CommandHandler("help", start))

    # Create background task
    application.job_queue.run_once(
        callback=lambda ctx: asyncio.create_task(check_containers(ctx)),
        when=0
    )

    logger.info("Starting Docker Monitor Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
