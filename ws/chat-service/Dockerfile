FROM python:3.12-slim
WORKDIR /app
COPY chat-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY _shared /app/_shared
COPY chat-service /app
