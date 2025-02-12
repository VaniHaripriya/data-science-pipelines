FROM python:3.14.0a1-slim

RUN pip install azure-devops

COPY queue-pipeline/src/queue_pipeline.py /scripts/queue_pipeline.py

ENTRYPOINT [ "bash" ]
