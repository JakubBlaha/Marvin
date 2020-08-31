FROM python:3.8.3
WORKDIR /usr/app/
RUN apt-get update
RUN apt-get install poppler-utils -y
RUN pip install pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --skip-lock
COPY . .
CMD [ "pipenv", "run", "python", "src/main.py" ]