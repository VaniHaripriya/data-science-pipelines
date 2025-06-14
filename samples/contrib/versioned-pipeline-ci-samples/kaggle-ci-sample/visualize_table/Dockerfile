FROM python:3.13.5
COPY requirements.txt .
RUN python3 -m pip install -r \
    requirements.txt --quiet --no-cache-dir \
    && rm -f requirements.txt
COPY ./visualize.py .
CMD ["python", 'visualize.py']