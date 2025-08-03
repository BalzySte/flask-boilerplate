FROM python:3.11-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "/usr/src/app"

# install system dependencies
# build essentials might be required on some platforms to build some python packages
RUN apt-get update && apt-get install -y git build-essential

# install dependencies
RUN pip install --upgrade pip && pip install poetry
COPY ./pyproject.toml ./poetry.lock /usr/src/app/ 
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --only main

# copy project
COPY flask-boilerplate/ /usr/src/app/

CMD ["python3", "webapp.py"]
