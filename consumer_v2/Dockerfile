FROM python:3.10-slim

WORKDIR /app

COPY ./consumer_v2/ ./consumer_v2/

COPY ./clients/ ./clients/

COPY ./models/ ./models/

COPY ./consumer/__init__.py ./consumer/__init__.py
COPY ./consumer/processing_utils.py ./consumer/processing_utils.py

COPY logger.py .

WORKDIR /app/consumer_v2

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app

CMD ["dramatiq", "consumer_v2.consumer_v2", "-p", "4", "-t", "4"]