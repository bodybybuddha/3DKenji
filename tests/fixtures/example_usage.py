"""Example script showing how to use test factories."""

from tests.fixtures.factories import (
    UserFactory,
    ProjectFactory,
    APIKeyFactory,
    BoundaryValueFactory,
)


def example_basic_usage():
    """Basic usage of factories."""
    
    # Create a user with defaults
    user1 = UserFactory.build()
    print(f"User 1: {user1}")
    
    # Create a user with custom values
    user2 = UserFactory.build(
        username="customuser",
        email="custom@example.com"
    )
    print(f"User 2: {user2}")
    
    # Create multiple users
    users = UserFactory.build_batch(5)
    print(f"Created {len(users)} users")


def example_invalid_data():
    """
    Generate invalid data for testing validation.
    """
    
    # Get all invalid username variations
    print("\nInvalid Usernames:")
    for variant, user_data in UserFactory.build_invalid("username"):
        print(f"  {variant}: {user_data['username']}")
    
    # Get all invalid email variations
    print("\nInvalid Emails:")
    for variant, user_data in UserFactory.build_invalid("email"):
        print(f"  {variant}: {user_data['email']}")


def example_boundary_values():
    """Test boundary values."""
    
    print("\nString Boundaries (max=50):")
    for label, value in BoundaryValueFactory.string_boundaries(max_length=50):
        print(f"  {label}: length={len(value)}")
    
    print("\nNumber Boundaries:")
    for label, value in BoundaryValueFactory.number_boundaries():
        print(f"  {label}: {value}")


def example_projects():
    """Project factory examples."""
    
    # Normal project
    project1 = ProjectFactory.build()
    print(f"\nProject 1: {project1}")
    
    # Project with special characteristics
    project2 = ProjectFactory.build_with_unicode()
    print(f"Project 2: {project2}")
    
    project3 = ProjectFactory.build_with_long_name()
    print(f"Project 3: name length = {len(project3['name'])}")


def example_api_keys():
    """API key factory examples."""
    
    # Key without expiration
    key1 = APIKeyFactory.build()
    print(f"\nKey 1: {key1}")
    
    # Key with expiration
    key2 = APIKeyFactory.build_with_expiration(days=30)
    print(f"Key 2: {key2}")
    
    # Key with scopes
    key3 = APIKeyFactory.build_with_scopes(["read:projects", "write:projects"])
    print(f"Key 3: {key3}")


if __name__ == "__main__":
    print("=" * 60)
    print("Test Factory Examples")
    print("=" * 60)
    
    example_basic_usage()
    example_invalid_data()
    example_boundary_values()
    example_projects()
    example_api_keys()
    
    print("\n" + "=" * 60)
    print("See tests/fixtures/factories.py for full API")
    print("=" * 60)
