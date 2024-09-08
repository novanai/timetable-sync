FROM python:3.12.5-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install -y python3-icu

COPY bot/requirements.txt bot/requirements.txt
COPY timetable/requirements.txt timetable/requirements.txt
RUN pip install -r bot/requirements.txt -r timetable/requirements.txt

COPY bot bot
COPY timetable timetable

# TODO: add optimization flags
CMD [ "python3", "-m", "bot" ]
