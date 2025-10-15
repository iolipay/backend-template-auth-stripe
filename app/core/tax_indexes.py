"""
Database indexes for tax declarations collection

Run this script to create indexes for optimal query performance:
    python -m app.core.tax_indexes
"""

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tax_indexes():
    """Create indexes for tax_declarations collection"""

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    logger.info("Creating indexes for tax_declarations collection...")

    # Create indexes
    await db.tax_declarations.create_index(
        [("user_id", 1), ("year", 1), ("month", 1)],
        unique=True,
        name="user_year_month_unique"
    )
    logger.info("✓ Created unique index on user_id + year + month")

    await db.tax_declarations.create_index(
        [("user_id", 1), ("status", 1)],
        name="user_status"
    )
    logger.info("✓ Created index on user_id + status")

    await db.tax_declarations.create_index(
        [("filing_deadline", 1)],
        name="filing_deadline"
    )
    logger.info("✓ Created index on filing_deadline")

    await db.tax_declarations.create_index(
        [("user_id", 1), ("year", 1)],
        name="user_year"
    )
    logger.info("✓ Created index on user_id + year")

    await db.tax_declarations.create_index(
        [("status", 1), ("filing_deadline", 1)],
        name="status_deadline"
    )
    logger.info("✓ Created index on status + filing_deadline")

    # List all indexes
    indexes = await db.tax_declarations.list_indexes().to_list(length=None)
    logger.info("\nAll indexes on tax_declarations:")
    for idx in indexes:
        logger.info(f"  - {idx['name']}: {idx.get('key', {})}")

    client.close()
    logger.info("\n✅ Tax declaration indexes created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tax_indexes())
