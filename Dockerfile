FROM python:alpine

# Install system dependencies
RUN apk add --no-cache docker-cli

# Install Python dependencies
RUN pip install --no-cache-dir docker python-telegram-bot python-telegram-bot[job-queue]

# Create app directory and non-root user
RUN adduser -D appuser && \
    mkdir /app && \
    chown appuser:appuser /app

WORKDIR /app
USER appuser

COPY --chown=appuser:appuser src/ /app/

ENV TELEGRAM_BOT_TOKEN=""
ENV TELEGRAM_CHAT_ID=""
ENV MONITOR_INTERVAL=5

CMD ["python", "bot.py"]
