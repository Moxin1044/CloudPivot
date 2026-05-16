# ===== Build Stage: Frontend =====
FROM node:20-alpine AS frontend-builder
WORKDIR /app/cloudpivot-web
COPY cloudpivot-web/package*.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY cloudpivot-web/ ./
RUN npm run build

# ===== Build Stage: Backend =====
FROM python:3.12-slim AS backend-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ===== Production Stage =====
FROM python:3.12-slim
LABEL maintainer="CloudPivot Team"

# Use Chinese apt mirror
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend code
COPY . .

# Copy frontend build output (after backend code to avoid being overwritten)
COPY --from=frontend-builder /app/cloudpivot-web/dist /app/static

# Create logs directory
RUN mkdir -p /app/logs

# Environment
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
