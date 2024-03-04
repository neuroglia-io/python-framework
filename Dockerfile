FROM python:3.12-slim as python-base

EXPOSE 80

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app 

# Pip
# COPY requirements.txt /app/
# RUN python -m pip install -r requirements.txt

# Poetry
COPY poetry.lock pyproject.toml /app/
RUN pip install poetry
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
ENV PYTHONPATH="src"
CMD ["uvicorn", "samples.openbank.api.main:app", "--host", "0.0.0.0", "--port", "80"]
