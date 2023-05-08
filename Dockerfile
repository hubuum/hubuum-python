# Build stage
FROM python:3.11-alpine as builder
WORKDIR /opt/hubuum
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ARG ENVIRONMENT="production"
RUN apk update
RUN apk upgrade
RUN apk add --virtual build-deps gcc python3-dev musl-dev libffi-dev postgresql-dev

COPY requirements*.txt /opt/hubuum/
RUN mkdir /opt/hubuum/wheels
# Always build complete environment to allow for testing of the actual
# production container.
RUN pip wheel --no-cache-dir --wheel-dir /opt/hubuum/wheels -r requirements-test.txt

# Final stage
FROM python:3.11-alpine
EXPOSE 8099
ENV PYTHONUNBUFFERED 1

COPY requirements*.txt entrypoint.sh manage.py /app/
COPY hubuum /app/hubuum/
COPY hubuumsite /app/hubuumsite/

COPY --from=builder /opt/hubuum/wheels /wheels

RUN apk update
RUN apk upgrade
RUN apk add --no-cache python3 py3-pip libstdc++ postgresql-libs
RUN pip install --no-cache /wheels/*
RUN rm -rf /wheels

LABEL org.opencontainers.image.source="https://github.com/terjekv/hubuum"
LABEL org.opencontainers.image.description="hubuum container image"
LABEL org.opencontainers.image.licenses="CC0-1.0"

WORKDIR /app
CMD ["/app/entrypoint.sh"]
