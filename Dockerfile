FROM python:3.11.5

COPY requirements.txt ./

RUN python3.11 -m pip install -r requirements.txt

COPY . ./

CMD [ "sanic", "timetable.server", "--host", "0.0.0.0", "--port", "80"]