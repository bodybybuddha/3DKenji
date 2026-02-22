#!/usr/bin/env python3
"""Create dummy user accounts for testing."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import uuid
from backend.models.user import User
from backend.plugins.auth_password import PasswordAuthProvider
from backend.db import get_session_factory
from backend.services.user_service import UserService

def create_dummy_users():
    """Create 5 dummy user accounts."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    
    dummy_users = [
        {
            "username": "alice_smith",
            "email": "alice.smith@example.com",
            "display_name": "Alice Smith",
            "password": "password123",
            "is_admin": False
        },
        {
            "username": "bob_jones",
            "email": "bob.jones@example.com",
            "display_name": "Bob Jones",
            "password": "password123",
            "is_admin": False
        },
        {
            "username": "carol_white",
            "email": "carol.white@example.com",
            "display_name": "Carol White",
            "password": "password123",
            "is_admin": False
        },
        {
            "username": "dave_brown",
            "email": "dave.brown@example.com",
            "display_name": "Dave Brown",
            "password": "password123",
            "is_admin": True
        },
        {
            "username": "eve_garcia",
            "email": "eve.garcia@example.com",
            "display_name": "Eve Garcia",
            "password": "password123",
            "is_admin": False
        }
    ]
    
    created_users = []
    
    try:
        for user_data in dummy_users:
            # Check if user already exists
            existing_user = session.query(User).filter(
                (User.username == user_data["username"]) | 
                (User.email == user_data["email"])
            ).first()
            
            if existing_user:
                print(f"❌ User {user_data['username']} already exists, skipping")
                continue
            
            # Create user
            new_user = User(
                id=str(uuid.uuid4()),
                username=user_data["username"],
                email=user_data["email"],
                display_name=user_data["display_name"],
                password_hash=UserService._hash_password(user_data["password"]),
                is_admin=user_data["is_admin"],
                is_active=True
            )
            
            session.add(new_user)
            created_users.append(user_data["username"])
            print(f"✅ Created user: {user_data['username']} ({user_data['email']})")
        
        session.commit()
        print(f"\n🎉 Successfully created {len(created_users)} dummy users!")
        print("\nTest credentials (all passwords: password123):")
        for user_data in dummy_users:
            role = "Admin" if user_data["is_admin"] else "User"
            print(f"  - {user_data['username']} ({role})")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating users: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    create_dummy_users()
