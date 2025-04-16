FROM python:3.10-slim

WORKDIR /app

COPY ./consumer/ ./consumer/

COPY ./clients/ ./clients/

COPY ./models/ ./models/

COPY logger.py .

WORKDIR /app/consumer

RUN pip install --no-cache-dir -r requirements.txt

RUN pytest --maxfail=1 --disable-warnings -v

RUN rm test_parsing.py feed_example.xml

WORKDIR /app

CMD ["python", "-m", "consumer.consumer"]