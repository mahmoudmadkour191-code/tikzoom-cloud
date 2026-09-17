FROM python:3.9.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /ecommerce-telegram-bot

RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    gcc \
    musl-dev

RUN python3 -m pip install pip==23.0.1

ADD requirements.txt /ecommerce-telegram-bot

RUN python3 -m pip install -r requirements.txt

EXPOSE 8000

COPY . /ecommerce-telegram-bot
