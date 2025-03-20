from datetime import datetime
from typing import List, Optional, AsyncGenerator
import asyncio
from bson import ObjectId
from app.schemas.chat import MessageRole, MessageCreate, ChatCreate, ChatUpdate
import random

class ChatService:
    def __init__(self, db):
        self.db = db

    async def create_chat(self, user_id: str, chat_data: ChatCreate) -> dict:
        """Create a new chat"""
        current_time = datetime.utcnow()
        chat_dict = chat_data.dict()
        chat_dict.update({
            "user_id": user_id,
            "created_at": current_time,
            "updated_at": current_time
        })
        
        result = await self.db.chats.insert_one(chat_dict)
        chat_dict["id"] = str(result.inserted_id)
        return chat_dict

    async def get_chat(self, chat_id: str, user_id: str) -> Optional[dict]:
        """Get a chat by ID"""
        chat = await self.db.chats.find_one({"_id": ObjectId(chat_id), "user_id": user_id})
        if chat:
            chat["id"] = str(chat.pop("_id"))
            return chat
        return None

    async def update_chat(self, chat_id: str, user_id: str, chat_data: ChatUpdate) -> Optional[dict]:
        """Update chat details"""
        update_data = {
            "$set": {
                **chat_data.dict(exclude_unset=True),
                "updated_at": datetime.utcnow()
            }
        }
        
        result = await self.db.chats.update_one(
            {"_id": ObjectId(chat_id), "user_id": user_id},
            update_data
        )
        
        if result.modified_count:
            return await self.get_chat(chat_id, user_id)
        return None

    async def delete_chat(self, chat_id: str, user_id: str) -> bool:
        """Delete a chat"""
        result = await self.db.chats.delete_one({"_id": ObjectId(chat_id), "user_id": user_id})
        return result.deleted_count > 0

    async def list_chats(self, user_id: str, skip: int = 0, limit: int = 20) -> List[dict]:
        """List user's chats with pagination"""
        cursor = self.db.chats.find({"user_id": user_id})
        cursor.sort("updated_at", -1).skip(skip).limit(limit)
        
        chats = []
        async for chat in cursor:
            chat["id"] = str(chat.pop("_id"))
            # Extract last message if available
            if chat.get("messages"):
                chat["last_message"] = chat["messages"][-1]
                chat.pop("messages")
            else:
                chat["last_message"] = None
            chats.append(chat)
            
        return chats

    async def add_message(self, chat_id: str, user_id: str, message: MessageCreate) -> Optional[dict]:
        """Add a message to a chat"""
        message_dict = message.dict()
        message_dict["created_at"] = datetime.utcnow()
        
        result = await self.db.chats.update_one(
            {"_id": ObjectId(chat_id), "user_id": user_id},
            {
                "$push": {"messages": message_dict},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count:
            return await self.get_chat(chat_id, user_id)
        return None

    async def stream_chat_response(self, user_message: str, chat_id: Optional[str] = None, user_id: str = None) -> AsyncGenerator[str, None]:
        """
        Stream a chat response for the given user message.
        If chat_id is provided, add to existing chat, otherwise create a new one.
        """
        # Sample responses for demonstration
        responses = [
            "I'm a streaming AI assistant, providing a response word by word.",
            "This is a demonstration of streaming capabilities in FastAPI.",
            "You can replace this with actual AI model integration.",
            "Streaming allows for more responsive user experience as content appears gradually.",
            "In a production environment, you would connect to an actual LLM API here."
        ]
        
        # Select a random response for demonstration
        response = random.choice(responses)
        words = response.split()
        
        # Create or get chat
        if chat_id:
            chat = await self.get_chat(chat_id, user_id)
            if not chat:
                # Create new chat if ID not found
                chat_data = ChatCreate(title=user_message[:30])
                chat = await self.create_chat(user_id, chat_data)
                chat_id = chat["id"]
        else:
            # Create new chat
            chat_data = ChatCreate(title=user_message[:30])
            chat = await self.create_chat(user_id, chat_data)
            chat_id = chat["id"]
        
        # Add user message to chat
        user_message_obj = MessageCreate(role=MessageRole.USER, content=user_message)
        await self.add_message(chat_id, user_id, user_message_obj)
        
        # Stream response
        full_response = ""
        for word in words:
            full_response += word + " "
            yield {"text": word + " ", "chat_id": chat_id}
            await asyncio.sleep(0.1)  # Simulate delay for streaming
        
        # Save assistant's complete response to the database
        assistant_message = MessageCreate(role=MessageRole.ASSISTANT, content=full_response.strip())
        await self.add_message(chat_id, user_id, assistant_message) 