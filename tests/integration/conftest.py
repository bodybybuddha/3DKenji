"""
Pytest configuration for integration tests.

Ensures test data exists (admin user, etc.) before running tests.
"""

import os
import pytest
import psycopg2
import bcrypt
from uuid import uuid4


@pytest.fixture(scope="session", autouse=True)
def ensure_test_admin_user():
    """Ensure the admin user exists in the database before running tests."""
    # Only run if we have a database available
    db_host = os.environ.get("DATABASE_HOST", "localhost")
    db_port = int(os.environ.get("DATABASE_PORT", 5432))
    db_name = os.environ.get("DATABASE_NAME", "kenji")
    db_user = os.environ.get("DATABASE_USER", "kenji")
    db_password = os.environ.get("DATABASE_PASSWORD", "kenji")
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
    except Exception as e:
        print(f"Could not connect to database: {e}")
        print("Tests requiring admin user will be skipped")
        return
    
    try:
        cur = conn.cursor()
        
        # Check if admin user exists
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        admin = cur.fetchone()
        
        if not admin:
            # Create admin user with proper bcrypt hashing
            admin_id = str(uuid4())
            password_hash = bcrypt.hashpw(
                "admin1234".encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            cur.execute("""
                INSERT INTO users (id, username, email, password_hash, is_admin, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                admin_id,
                "admin",
                "admin@local.test",
                password_hash,
                True,
                True
            ))
            conn.commit()
            print("✓ Test admin user created")
        else:
            print("✓ Test admin user already exists")
        
        cur.close()
        
    except Exception as e:
        print(f"Error setting up test admin user: {e}")
    finally:
        conn.close()
