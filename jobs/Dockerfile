FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir google-cloud-bigquery
COPY sync_events.py sync_spaces.py ./
CMD ["python", "sync_events.py"]
