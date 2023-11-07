FROM python:3.11.5

RUN useradd -ms /bin/bash tt-sync
USER tt-sync

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN [ "python3", "-m", "mkdocs", "build" ]

CMD [ "python3", "-m", "timetable" ]