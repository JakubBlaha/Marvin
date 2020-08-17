FROM python:3.8.3
RUN pip install pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --skip-lock
COPY . .
CMD [ "pipenv", "run", "python", "src/main.py" ]