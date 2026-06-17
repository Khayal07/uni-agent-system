FROM python:3.10-slim

WORKDIR /code

# Eyni qovluqdakı requirements.txt-ni köçürüb yükləyirik
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# backend qovluğunun içindəki hər şeyi (app, tests və s.) bütöv köçürürük
COPY . /code/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]