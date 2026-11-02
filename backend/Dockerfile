FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# No Docker o banco é o PostgreSQL do docker-compose, então o driver entra aqui
# (fora do requirements.txt pra não quebrar quem roda local com SQLite).
RUN pip install --no-cache-dir "psycopg[binary]>=3.2"

COPY app ./app
# Sem esta linha o .joblib não entrava na imagem e /recognition respondia 503.
COPY models ./models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
