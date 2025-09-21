# Multi-stage build for smaller image
FROM python:3.10-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/streamlit/.local/bin:$PATH \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash streamlit && \
    mkdir -p /app /app/data /app/logs /app/.streamlit/cache /app/utils && \
    chown -R streamlit:streamlit /app

# Copy Python packages from builder
COPY --from=builder --chown=streamlit:streamlit /root/.local /home/streamlit/.local

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=streamlit:streamlit . .

# Ensure utils directory has all necessary files
COPY --chown=streamlit:streamlit utils/ /app/utils/

# Create necessary directories and set permissions
RUN mkdir -p /app/.streamlit && \
    echo '[server]\nport = 8501\naddress = "0.0.0.0"\nheadless = true\n\n[browser]\ngatherUsageStats = false' > /app/.streamlit/config.toml && \
    chown -R streamlit:streamlit /app

# Switch to non-root user
USER streamlit

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Set the entrypoint
ENTRYPOINT ["streamlit", "run"]

# Set the default command
CMD ["app.py", "--server.port=8501", "--server.address=0.0.0.0"]