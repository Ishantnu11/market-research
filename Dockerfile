# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with FastAPI
FROM python:3.12-slim-bookworm
WORKDIR /app

# Set non-interactive for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir aiofiles uvicorn

# Copy the built frontend from Stage 1
COPY --from=frontend-builder /app/dist ./dist

# Copy the backend code
COPY . .

# Set environment variables
ENV PORT=8080
ENV GEMINI_MODEL=gemini-2.5-flash

# Expose the port
EXPOSE 8080

# Command to run the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
