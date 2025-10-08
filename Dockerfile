FROM python:3.12-alpine

RUN apk update \
    apk add musl-dev libpq-dev gcc

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "./main.py" ]
