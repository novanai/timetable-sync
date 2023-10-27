FROM python:3.11.5

RUN useradd -ms /bin/bash tt-sync
USER tt-sync

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python3", "-m", "timetable" ]