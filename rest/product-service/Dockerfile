FROM python:3.12-slim
WORKDIR /app
COPY product-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY _shared /app/_shared
COPY product-service /app
