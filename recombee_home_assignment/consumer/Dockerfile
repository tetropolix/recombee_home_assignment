FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir pytest

COPY consumer.py .
COPY parser.py .
COPY test_feed_parser.py .
COPY feed_example.xml .

RUN pytest --maxfail=1 --disable-warnings -v

RUN rm test_feed_parser.py feed_example.xml

CMD ["python", "consumer.py"]