from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str
    created_at: datetime = datetime.utcnow()

class Chat(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    messages: List[Message] = []
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow() 