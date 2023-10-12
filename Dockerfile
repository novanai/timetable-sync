FROM python:3.11.5

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd -ms /bin/bash tt-sync
RUN chown -R tt-sync /app
USER tt-sync

CMD [ "python3", "-m", "timetable" ]