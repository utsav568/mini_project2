# GuardianNodes RoadSoS - Production Dockerfile
FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure data and evidence directories exist
RUN mkdir -p roadsafety/data/evidence

# Make start script executable
RUN chmod +x start.sh

# Expose FastAPI (:8000) and Streamlit CAD (:8501)
EXPOSE 8000 8501

# Run both services
CMD ["./start.sh"]
