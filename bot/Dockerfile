FROM python:3.12.6-slim

WORKDIR /app

RUN apt-get update && apt-get install -y python3-icu

COPY bot/requirements.txt bot/requirements.txt
COPY timetable/requirements.txt timetable/requirements.txt
RUN pip install -r bot/requirements.txt -r timetable/requirements.txt

COPY bot bot
COPY timetable timetable

CMD [ "python3", "-OOm", "bot" ]
