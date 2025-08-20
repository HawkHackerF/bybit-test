
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Expect config.yaml to be mounted or copied in
CMD ["python", "bot.py"]
