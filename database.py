import os
import psycopg

def get_connection():
    return psycopg.connect(
        host="localhost",
        port="5432",
        dbname="submission_system",
        user="postgres",
        password="anita0306"
    )