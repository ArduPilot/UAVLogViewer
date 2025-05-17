import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv
from models.database import init_db, get_database_url

def setup_database():
    """
    Set up the PostgreSQL database for the UAV Logger.
    This script will:
    1. Create the database if it doesn't exist
    2. Initialize all tables
    """
    load_dotenv()

    # Get database connection parameters
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "uav_logger")

    # Connect to PostgreSQL server (without specifying a database)
    conn = psycopg2.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database {db_name}...")
            cursor.execute(f'CREATE DATABASE {db_name}')
            print(f"Database {db_name} created successfully!")
        else:
            print(f"Database {db_name} already exists.")

    finally:
        cursor.close()
        conn.close()

    # Initialize tables
    print("Initializing database tables...")
    init_db(get_database_url())
    print("Database setup completed successfully!")

if __name__ == "__main__":
    setup_database() 