FROM python:3.7

EXPOSE 80

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
