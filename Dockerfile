FROM python:3.12-slim

ARG HOST_UID=1000
ARG HOST_GID=1000

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${HOST_GID} appuser || groupadd appuser
RUN useradd -u ${HOST_UID} -g appuser -m -s /bin/bash appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy config and data files
COPY pulse_events.toml .
COPY major_events.toml .
COPY actions.toml .  
COPY entities.toml .
COPY initial_incidents.sql .

# Copy all application source code
COPY . .

RUN chmod +x entrypoint.sh
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD []
