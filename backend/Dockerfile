FROM python:3.12-slim-bookworm

WORKDIR /workspace

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose port
EXPOSE 8000

# Production: use $PORT injected by Railway (fallback 8000), no --reload
# Shell form is required to expand env variables like $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1

