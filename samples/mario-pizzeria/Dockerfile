FROM python:3.12-slim AS python-base

EXPOSE 8080 5678

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Poetry - Install dependencies first
COPY poetry.lock pyproject.toml /app/
RUN pip install poetry
RUN poetry config virtualenvs.create false && \
    (poetry lock 2>/dev/null || true) && \
    poetry install --no-root --no-interaction --no-ansi --extras mongodb

# Copy the entire project
COPY . /app

# Install the project itself after copying all files
RUN poetry install --only-root --no-interaction --no-ansi

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
ENV PYTHONPATH="src"

# Default command for Mario's Pizzeria
CMD ["uvicorn", "samples.mario-pizzeria.main:app", "--host", "0.0.0.0", "--port", "8080"]
