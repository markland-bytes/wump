FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /code

# Copy dependency files and README (required by hatchling)
COPY pyproject.toml uv.lock README.md ./

# Copy application code
COPY src ./src

# Copy alembic migration files
COPY alembic ./alembic
COPY alembic.ini ./

# Copy entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Install dependencies using uv sync (includes all extras for dev tools)
RUN uv sync --locked --all-extras

# Add the virtual environment to PATH
ENV PATH="/code/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Run migrations and start the application
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
