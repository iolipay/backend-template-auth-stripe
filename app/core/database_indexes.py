"""
Database indexes for optimal query performance.

Run this module once after setting up the database to create indexes.
You can run it with: python -m app.core.database_indexes
"""

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_indexes():
    """Create all necessary database indexes"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    logger.info("Creating database indexes...")

    # Users collection indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("stripe_customer_id")
    await db.users.create_index("verification_token")
    logger.info("✓ Created indexes for 'users' collection")

    # Transactions collection indexes
    await db.transactions.create_index([("user_id", 1), ("transaction_date", -1)])
    await db.transactions.create_index([("user_id", 1), ("type", 1)])
    await db.transactions.create_index([("user_id", 1), ("currency", 1)])
    await db.transactions.create_index([("user_id", 1), ("category", 1)])
    await db.transactions.create_index("created_at")
    logger.info("✓ Created indexes for 'transactions' collection")

    # Chats collection indexes
    await db.chats.create_index([("user_id", 1), ("updated_at", -1)])
    await db.chats.create_index("created_at")
    logger.info("✓ Created indexes for 'chats' collection")

    logger.info("All indexes created successfully!")

    client.close()


if __name__ == "__main__":
    asyncio.run(create_indexes())
