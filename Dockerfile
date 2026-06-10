FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# gcc / libc6-dev / libpq-dev: psycopg2 は sdist のみ配布のためビルドに必要
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --system --dev

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
