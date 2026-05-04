FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/agents/scheduler/

CMD ["python", "/app/agents/scheduler/main.py"]
