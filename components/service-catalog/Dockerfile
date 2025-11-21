FROM python:3.13-alpine3.22 AS base

WORKDIR /svc

COPY requirements.txt requirements.txt
RUN rm -rf /var/cache/apk/* && rm -rf /tmp/*
RUN apk update && apk add --update python3 && rm -rf /var/cache/apk/* && \
    pip install --upgrade pip && \
    pip wheel -r requirements.txt --wheel-dir=/svc/wheels

WORKDIR /app
COPY src/app.py /app/app.py
COPY src/library/ /app/library/


FROM python:3.13-alpine3.22

COPY --from=base /svc /svc
RUN pip install --no-index --find-links=/svc/wheels --trusted-host pypi.python.org -r /svc/requirements.txt

COPY --from=base /app /app
WORKDIR /app
#CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["gunicorn", "app:app","--workers 12","--worker-class","uvicorn.workers.UvicornWorker","--bind", "0.0.0.0:8000"]
