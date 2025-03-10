FROM python:3.11-alphine AS base
ARG DATABASE_URL
ARG BOT_TOKEN

FROM base AS installer
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM installer AS runner
WORKDIR /app
CMD [ "python","./folder/bot2.py" ]
