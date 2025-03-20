from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageCreate(BaseModel):
    role: MessageRole
    content: str

class MessageResponse(MessageCreate):
    created_at: datetime

class ChatCreate(BaseModel):
    title: Optional[str] = None
    messages: List[MessageCreate] = []

class ChatUpdate(BaseModel):
    title: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

class ChatListResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    last_message: Optional[MessageResponse] = None
    created_at: datetime
    updated_at: datetime

class StreamRequest(BaseModel):
    message: str = Field(..., description="User message to send to the chat")
    chat_id: Optional[str] = Field(None, description="Chat ID for continuing an existing chat") 