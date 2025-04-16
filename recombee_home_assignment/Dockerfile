FROM python:3.10-slim

WORKDIR /app

COPY ./clients/ ./clients/

COPY ./models/ ./models/

COPY logger.py .

COPY requirements.txt .

COPY main.py .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]