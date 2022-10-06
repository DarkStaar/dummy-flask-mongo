FROM python:3

ENV FLASK_APP=app.py

ENV FLASK_RUN_HOST=0.0.0.0

RUN pip install --upgrade pip

WORKDIR /ms-identity-python-webapp

RUN ls .

COPY requirements.txt .

RUN pip3 install -r requirements.txt

EXPOSE 5000

CMD flask run