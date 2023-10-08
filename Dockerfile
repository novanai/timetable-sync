FROM python:3.11.5

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd -ms /bin/bash tt-sync
USER tt-sync

CMD [ "sanic", "timetable.server", "--host", "0.0.0.0", "--port", "80", "--debug" ]