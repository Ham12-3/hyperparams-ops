FROM python:3.12-slim

RUN pip install --no-cache-dir mlflow==2.20.2 psycopg2-binary==2.9.10

RUN mkdir -p /mlflow/artifacts

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
