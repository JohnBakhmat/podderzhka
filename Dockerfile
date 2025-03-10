FROM python:3.11.11-alpine AS base
ARG DATABASE_URL
ARG BOT_TOKEN

FROM base AS installer
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD [ "python","src/bot2.py" ]
