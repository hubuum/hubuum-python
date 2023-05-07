# Build stage
FROM python:3.11-alpine as builder
WORKDIR /opt/hubuum
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ARG ENVIRONMENT="production"
RUN apk update
RUN apk add --virtual build-deps gcc python3-dev musl-dev libffi-dev postgresql-dev

COPY requirements*.txt /opt/hubuum/
RUN mkdir /opt/hubuum/wheels
RUN pip install --upgrade pip
RUN if [ "$ENVIRONMENT" = "testing" ] ; then \
        pip wheel --no-cache-dir --wheel-dir /opt/hubuum/wheels -r requirements-test.txt; \
    else \
        pip wheel --no-cache-dir --wheel-dir /opt/hubuum/wheels -r requirements.txt; \
    fi

# Final stage
FROM python:3.11-alpine
EXPOSE 8099
ENV PYTHONUNBUFFERED 1

ARG ENVIRONMENT="production"
COPY requirements*.txt entrypoint.sh manage.py /app/
COPY hubuum /app/hubuum/
COPY hubuumsite /app/hubuumsite/

COPY --from=builder /opt/hubuum/wheels /wheels

RUN apk update && apk upgrade && apk add --no-cache  python3 py3-pip  libstdc++ postgresql-libs \
    && pip install --upgrade pip \
    && pip install --no-cache /wheels/* \
    && rm -rf /wheels


WORKDIR /app
CMD ["/app/entrypoint.sh"]
