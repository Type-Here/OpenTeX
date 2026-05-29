"""Apply MongoDB validators for OpenTeX collections."""


import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure

from db.config import get_db_name, get_mongodb_uri
from scripts.validation.schema_validation import get_validators


async def apply_validators(db) -> None:
    """Create or update collection validators in the target database."""
    validators = get_validators()
    existing = set(await db.list_collection_names())

    for name, validator in validators.items():
        if name in existing:
            try:
                await db.command(
                    {
                        "collMod": name,
                        "validator": validator,
                        "validationLevel": "strict",
                        "validationAction": "error",
                    }
                )
                print(f"Updated validator for collection: {name}")
            except OperationFailure as exc:
                print(f"Failed to update validator for {name}: {exc}")
        else:
            await db.create_collection(
                name,
                validator=validator,
                validationLevel="strict",
                validationAction="error",
            )
            print(f"Created collection with validator: {name}")


async def main() -> None:
    """Connect to MongoDB and apply validators using configured settings."""
    mongo_uri = get_mongodb_uri()
    db_name = get_db_name()

    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]

    await db.command("ping")
    await apply_validators(db)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
