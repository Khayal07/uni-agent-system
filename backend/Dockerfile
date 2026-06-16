FROM python:3.11-slim

WORKDIR /backend

# Sistem asılılıqlarını yükləyirik (bazaya qoşulmaq və s. üçün lazım ola bilər)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Kitabxanaları köçürüb yükləyirik
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bütün backend kodunu konteynerə köçürürük
COPY . .

# FastAPI-ı uvicorn vasitəsilə işə salırıq
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]