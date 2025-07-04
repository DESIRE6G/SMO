# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/ .

# Provide defaults (optional, matches your Pydantic defaults)
ENV HOST=0.0.0.0 \
    PORT=8000

ENTRYPOINT ["sh", "-c", "uvicorn main:app --host $HOST --port $PORT"]
