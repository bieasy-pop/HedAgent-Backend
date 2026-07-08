"""
Promotes a user to super admin in the database.
Usage: python promote_admin.py
"""
from sqlalchemy import create_engine, text


def main():
    db_url = input("Paste your Render External Database URL: ").strip()
    email = input("Enter the user's email to promote: ").strip()

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check user exists
        result = conn.execute(
            text("SELECT id, email, role FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()

        if not user:
            print(f"\nNo user found with email: {email}")
            print("Make sure the user has registered first.")
            return

        print(f"\nFound user:")
        print(f"  ID    : {user[0]}")
        print(f"  Email : {user[1]}")
        print(f"  Role  : {user[2]}")

        confirm = input(f"\nPromote {email} to admin? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Cancelled.")
            return

        # Promote to admin
        conn.execute(
            text("UPDATE users SET role = 'admin' WHERE email = :email"),
            {"email": email}
        )
        conn.commit()

        # Verify
        result = conn.execute(
            text("SELECT id, email, role FROM users WHERE email = :email"),
            {"email": email}
        )
        updated = result.fetchone()
        print(f"\nDone! User updated:")
        print(f"  ID    : {updated[0]}")
        print(f"  Email : {updated[1]}")
        print(f"  Role  : {updated[2]}")
        print("\nThe user must log out and log back in for the new role to take effect.")


if __name__ == "__main__":
    main()
