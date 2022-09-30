FROM python:3.7.1

ENV FLASK_APP=server.py

ENV FLASK_RUN_HOST=0.0.0.0

RUN pip install --upgrade pip

WORKDIR /dummyfm

RUN ls .

COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 5000

CMD flask --app server run