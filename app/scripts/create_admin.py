#!/usr/bin/env python3
"""
Admin Account Creation Script

Usage:
    python -m app.scripts.create_admin

This script allows you to grant admin privileges to an existing user account.
The user must already be registered in the system.
"""

import asyncio
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import after path is set
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def create_admin():
    """Grant admin privileges to a user"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    print("=" * 60)
    print("Admin Account Creation")
    print("=" * 60)
    print()

    # Get user email
    email = input("Enter user email to grant admin privileges: ").strip()

    if not email:
        print("❌ Email cannot be empty")
        return

    # Check if user exists
    user = await db.users.find_one({"email": email})

    if not user:
        print(f"❌ User with email '{email}' not found")
        print("   Please register the user first via the API")
        return

    # Check if already admin
    if user.get("is_admin"):
        print(f"ℹ️  User '{email}' is already an admin")
        return

    # Confirm
    print()
    print(f"User found:")
    print(f"  Email: {user['email']}")
    print(f"  Created: {user.get('created_at', 'Unknown')}")
    print(f"  Verified: {user.get('is_verified', False)}")
    print()

    confirm = input("Grant admin privileges to this user? (yes/no): ").strip().lower()

    if confirm not in ["yes", "y"]:
        print("❌ Cancelled")
        return

    # Grant admin privileges
    result = await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "is_admin": True,
                "admin_since": datetime.now(timezone.utc)
            }
        }
    )

    if result.modified_count > 0:
        print()
        print("✅ Admin privileges granted successfully!")
        print(f"   User '{email}' is now an admin")
        print()
        print("The user can now access all /admin/* endpoints")
    else:
        print("❌ Failed to grant admin privileges")

    # Close connection
    client.close()


async def list_admins():
    """List all current admins"""

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    print()
    print("=" * 60)
    print("Current Admin Users")
    print("=" * 60)
    print()

    admins = []
    async for user in db.users.find({"is_admin": True}):
        admins.append(user)

    if not admins:
        print("No admin users found")
    else:
        for admin in admins:
            print(f"📧 {admin['email']}")
            print(f"   Admin since: {admin.get('admin_since', 'Unknown')}")
            print(f"   Verified: {admin.get('is_verified', False)}")
            print()

    client.close()


async def revoke_admin():
    """Revoke admin privileges from a user"""

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    print("=" * 60)
    print("Revoke Admin Privileges")
    print("=" * 60)
    print()

    email = input("Enter admin email to revoke privileges: ").strip()

    if not email:
        print("❌ Email cannot be empty")
        return

    user = await db.users.find_one({"email": email})

    if not user:
        print(f"❌ User with email '{email}' not found")
        return

    if not user.get("is_admin"):
        print(f"ℹ️  User '{email}' is not an admin")
        return

    confirm = input(f"Revoke admin privileges from '{email}'? (yes/no): ").strip().lower()

    if confirm not in ["yes", "y"]:
        print("❌ Cancelled")
        return

    result = await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "is_admin": False
            },
            "$unset": {
                "admin_since": ""
            }
        }
    )

    if result.modified_count > 0:
        print()
        print("✅ Admin privileges revoked successfully!")
        print(f"   User '{email}' is no longer an admin")
    else:
        print("❌ Failed to revoke admin privileges")

    client.close()


async def main():
    """Main menu"""

    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           Admin Account Management Script                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print("Options:")
    print("  1. Grant admin privileges to a user")
    print("  2. Revoke admin privileges from a user")
    print("  3. List all current admins")
    print("  4. Exit")
    print()

    choice = input("Select option (1-4): ").strip()

    if choice == "1":
        await create_admin()
    elif choice == "2":
        await revoke_admin()
    elif choice == "3":
        await list_admins()
    elif choice == "4":
        print("Goodbye!")
        return
    else:
        print("❌ Invalid option")
        return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
