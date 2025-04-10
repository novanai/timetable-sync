FROM python:3.12.6-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY timetable/requirements.txt timetable/requirements.txt
RUN pip install -r backend/requirements.txt -r timetable/requirements.txt

COPY backend backend
COPY timetable timetable

CMD python -OOm uvicorn backend.server:app --workers 4 --host 0.0.0.0 --port "${BACKEND_PORT}"
