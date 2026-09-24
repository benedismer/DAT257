# Dockerfile for the Flask app.
# Uses a slim official Python image to keep the build small and fast.

FROM python:3.12-slim

# Keep Python from writing .pyc files and buffering stdout/stderr,
# so logs show up immediately in `docker compose logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (separate layer) so Docker can cache them.
# Rebuilds only reinstall packages when requirements.txt actually changes.
# The build context is the project ROOT, and requirements.txt lives in docker/,
# so we reference it at that path. It is copied to /app/requirements.txt.
COPY docker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
# In development, docker-compose.yml mounts the source over this so your live
# edits are picked up without rebuilding. For a plain `docker build`/`docker run`
# (no compose), this baked-in copy is what runs.
COPY . .

# The Flask dev server listens on this port inside the container.
EXPOSE 5000

# Default command runs the app. Flask's debug reloader handles live reload.
CMD ["python", "app.py"]
