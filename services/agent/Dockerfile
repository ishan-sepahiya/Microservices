FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Streamlit runs on 8501, FastAPI on 8020
EXPOSE 8020 8501
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8020"]
