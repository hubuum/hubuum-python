# Build stage
FROM python:3.11-alpine as builder
WORKDIR /opt/hubuum
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VENV_PATH=/opt/venv

ARG ENVIRONMENT="production"

RUN apk update
RUN apk upgrade
RUN apk add --virtual build-deps gcc python3-dev musl-dev libffi-dev postgresql-dev

RUN pip3 install poetry
COPY pyproject.toml /opt/hubuum/
COPY poetry.lock /opt/hubuum/

# Always build complete environment to allow for testing of the actual
# production container.
RUN python -m venv $VENV_PATH
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi -vvv

# Final stage
FROM python:3.11-alpine
EXPOSE 8099
ENV PYTHONUNBUFFERED 1

COPY entrypoint.sh manage.py /app/
COPY hubuum /app/hubuum/
COPY hubuumsite /app/hubuumsite/

COPY --from=builder $VENV_PATH $VENV_PATH

RUN apk update
RUN apk upgrade
RUN apk add --no-cache python3 py3-pip libstdc++ postgresql-libs

LABEL org.opencontainers.image.source="https://github.com/terjekv/hubuum"
LABEL org.opencontainers.image.description="hubuum container image"
LABEL org.opencontainers.image.licenses="CC0-1.0"

WORKDIR /app
CMD ["/app/entrypoint.sh"]
