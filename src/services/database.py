from ..components.keys import MONGO_URL
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

mongo_client = AsyncIOMotorClient(MONGO_URL, server_api=ServerApi('1'))