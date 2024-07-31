FROM python:3.12.4

RUN useradd -ms /bin/bash tt-sync
USER tt-sync

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY timetable/requirements.txt timetable/requirements.txt
RUN pip install -r backend/requirements.txt -r timetable/requirements.txt

COPY backend backend
COPY timetable timetable

CMD ["python", "-m", "uvicorn", "backend.server:app", "--host=0.0.0.0", "--port=80", "--no-access-log"]
