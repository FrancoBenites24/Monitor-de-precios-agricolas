FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 monitor

COPY --chown=monitor:monitor app/ ./app/
COPY --chown=monitor:monitor data/ ./data/

USER monitor

CMD ["python", "-m", "app.bot_main"]
