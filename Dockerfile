# Single-image build: compile the React frontend, then serve it + the API from
# one FastAPI/uvicorn process. Deploys as one service on Render/Fly/Railway/AWS.

# --- stage 1: build frontend ---
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build      # -> /fe/dist

# --- stage 2: python runtime serving API + static frontend ---
FROM python:3.11-slim AS app
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /fe/dist ./frontend/dist
ENV PYTHONPATH=/app/backend
WORKDIR /app/backend
EXPOSE 8000
# $PORT is provided by most PaaS hosts; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
