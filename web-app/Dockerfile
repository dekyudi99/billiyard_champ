FROM python:3.10-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and assets
COPY backend ./backend
COPY frontend ./frontend
COPY logos ./logos
COPY trofi ./trofi

# Ensure database is pre-seeded if not present
WORKDIR /app/backend
RUN python seed_data.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

