FROM python:3.12

COPY requirements.txt requirements.txt

RUN python -m pip install --upgrade pip && pip install -r requirements.txt

WORKDIR /bot
COPY bot.py bot.py
COPY main.py main.py

ENTRYPOINT [ "python3", "bot.py" ]

