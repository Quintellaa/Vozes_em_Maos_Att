# Imagem para a nuvem (Render): backend + front-end num endereço só.
# O backend/Dockerfile continua valendo para o docker-compose local (só a API).
FROM python:3.12-slim

WORKDIR /code

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Na nuvem o banco é PostgreSQL (o SQLite seria apagado a cada reinício do servidor).
RUN pip install --no-cache-dir psycopg2-binary==2.9.10

COPY backend/app ./app
COPY backend/models ./models
COPY frontend ./frontend

ENV FRONTEND_DIR=/code/frontend
EXPOSE 8000
# O Render informa a porta em $PORT; localmente fica a 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
