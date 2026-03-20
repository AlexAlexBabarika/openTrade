# Multi-stage build: Node for frontend, Python for backend
FROM node:20-slim AS frontend-build
WORKDIR /app

# Vite resolves @shared -> ../shared relative to frontend/ — must exist at build time
COPY shared/ shared/

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY shared/ shared/
COPY backend/ backend/
COPY run_backend.py .
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY --from=frontend-build /app/frontend/dist frontend/dist
EXPOSE 8000
CMD ["python", "run_backend.py"]
