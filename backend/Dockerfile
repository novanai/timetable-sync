FROM python:3.12.6-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY timetable/requirements.txt timetable/requirements.txt
RUN pip install -r backend/requirements.txt -r timetable/requirements.txt

COPY backend backend
COPY timetable timetable

CMD ["python", "-m", "uvicorn", "backend.server:app", "--host=0.0.0.0", "--port=2000", "--no-access-log"]
