FROM python:3.13.4
COPY ./train.py .
COPY requirements.txt .
RUN python3 -m pip install -r \
    requirements.txt --quiet --no-cache-dir \
    && rm -f requirements.txt
CMD ["python", "train.py"]