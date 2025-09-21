FROM python:3.11-slim

WORKDIR /app
COPY app /app/app
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

RUN mkdir -p /out
VOLUME ["/out"]

ENTRYPOINT ["python", "-m", "app.cli"]
