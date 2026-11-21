FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY rag/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rag/app ./app
COPY rag/tests ./tests
COPY corpus ./corpus
RUN useradd -u 10001 -m rag
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
