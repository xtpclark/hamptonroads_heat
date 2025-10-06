#!/bin/bash
set -e

# Wait for Postgres
until PGPASSWORD="${POSTGRES_PASSWORD:-password}" pg_isready -h "postgres" -p "5432" -U "${POSTGRES_USER:-postgres}"; do
  echo "Postgres is unavailable - sleeping" >&2
  sleep 1
done

echo "Postgres is up - creating tables and seeding static data..." >&2

export PGPASSWORD="${POSTGRES_PASSWORD:-password}"
# Step 1: Create schema and seed static data that should always exist.
# Using ON CONFLICT DO NOTHING makes this safe to re-run.
psql -h "postgres" -p "5432" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-hamptonroads}" <<EOF
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS localities (
    id SERIAL PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL, lat FLOAT NOT NULL, lon FLOAT NOT NULL
);
DROP TABLE IF EXISTS incidents;
CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY, lat FLOAT NOT NULL, lon FLOAT NOT NULL, type VARCHAR(50) NOT NULL,
    weight INTEGER NOT NULL, gang_tag VARCHAR(50), shooter_race VARCHAR(50),
    funeral_id VARCHAR(50), timestamp TIMESTAMP NOT NULL, locality VARCHAR(50)
);
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY, type VARCHAR(50) NOT NULL, name VARCHAR(100) NOT NULL,
    geometry GEOMETRY(POINT, 4326) NOT NULL, locality VARCHAR(50)
);
CREATE TABLE IF NOT EXISTS sim_states (
    id SERIAL PRIMARY KEY, turn INTEGER NOT NULL, action VARCHAR(50) NOT NULL, outcome TEXT,
    budget FLOAT NOT NULL, backlash FLOAT NOT NULL, reputation FLOAT DEFAULT 50
);

INSERT INTO localities (name, lat, lon) VALUES ('Norfolk', 36.85, -76.28) ON CONFLICT (name) DO NOTHING;
EOF



# Step 2: Run the Python script to load entities from the TOML file
python load_entities.py


# Step 3: Check if the incidents table is empty.
# The -t flag gives "tuples only" output, making it easy to check.
INCIDENT_COUNT=$(psql -h "postgres" -p "5432" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-hamptonroads}" -t -c "SELECT COUNT(*) FROM incidents;")

# Step 3: If the table is empty, load the initial data from the backup file.
# We trim whitespace from the count to be safe.
if [ "$(echo ${INCIDENT_COUNT} | xargs)" = "0" ]; then
  echo "Incidents table is empty. Loading initial data from initial_incidents.sql..."
  psql -h "postgres" -p "5432" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-hamptonroads}" -f initial_incidents.sql
else
  echo "Incidents table already contains data. Skipping initial data load."
fi

unset PGPASSWORD

echo "Database is ready - executing Flask app" >&2
exec python app.py
