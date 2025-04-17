FROM python:3.10-slim

WORKDIR /app

COPY ./clients/ ./clients/

COPY ./models/ ./models/

# need to import the dramariq actor
COPY ./consumer_v2/__init__.py ./consumer_v2/c__init__.py 
COPY ./consumer_v2/consumer_v2.py ./consumer_v2/consumer_v2.py
COPY ./consumer/__init__.py ./consumer/__init__.py
COPY ./consumer/processing_utils.py ./consumer/processing_utils.py

COPY logger.py .

COPY requirements.txt .

COPY main.py .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]