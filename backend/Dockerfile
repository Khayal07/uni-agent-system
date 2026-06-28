FROM python:3.10-slim

WORKDIR /code

# Build konteksti layihə köküdür → backend/ və frontend/ ayrıca köçürülür
COPY backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Backend kodu /code-a, frontend faylları /frontend-ə
COPY backend/ /code/
COPY frontend/ /frontend/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]