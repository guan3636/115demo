
import os
import psycopg

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname="submission_system",
        user=os.getenv("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"]
    )
