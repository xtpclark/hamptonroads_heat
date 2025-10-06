# db.py
import os
import time
import logging
from sqlalchemy import create_engine, text

def connect_db():
    """Establishes and returns a database engine connection."""
    db_user = os.environ.get('POSTGRES_USER', 'postgres')
    db_pass = os.environ.get('POSTGRES_PASSWORD', 'password')
    db_name = os.environ.get('POSTGRES_DB', 'hamptonroads')
    db_host = 'postgres'
    conn_str = f'postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}'
    
    for _ in range(5):
        try:
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logging.info("Database connection successful.")
            return engine
        except Exception as e:
            logging.error(f"DB connection failed: {e}")
            time.sleep(2)
    raise Exception("Failed to connect to DB after multiple retries")

engine = connect_db()
