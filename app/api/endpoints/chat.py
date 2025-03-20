from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
import json
from app.api.deps import get_current_user, get_chat_service
from app.schemas.user import UserResponse
from app.schemas.chat import ChatCreate, ChatUpdate, ChatResponse, ChatListResponse, StreamRequest
from app.services.chat import ChatService

router = APIRouter(tags=["Chat"])

@router.post("/", 
    response_model=ChatResponse,
    description="Create a new chat",
    responses={
        201: {"description": "Chat created successfully"},
        401: {"description": "Not authenticated"}
    })
async def create_chat(
    chat_data: ChatCreate,
    current_user: UserResponse = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Create a new chat for the current user.
    Optionally include initial messages.
    """
    chat = await chat_service.create_chat(current_user.id, chat_data)
    return ChatResponse(**chat)

@router.get("/", 
    response_model=List[ChatListResponse],
    description="List user's chats",
    responses={
        200: {"description": "List of chats"},
        401: {"description": "Not authenticated"}
    })
async def list_chats(
    skip: int = 0,
    limit: int = 20,
    current_user: UserResponse = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> List[ChatListResponse]:
    """
    List all chats for the current user.
    Results are paginated and sorted by most recent first.
    """
    chats = await chat_service.list_chats(current_user.id, skip, limit)
    return [ChatListResponse(**chat) for chat in chats]

@router.get("/{chat_id}", 
    response_model=ChatResponse,
    description="Get chat details",
    responses={
        200: {"description": "Chat details"},
        401: {"description": "Not authenticated"},
        404: {"description": "Chat not found"}
    })
async def get_chat(
    chat_id: str,
    current_user: UserResponse = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Get details of a specific chat including all messages.
    """
    chat = await chat_service.get_chat(chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatResponse(**chat)

@router.put("/{chat_id}", 
    response_model=ChatResponse,
    description="Update chat details",
    responses={
        200: {"description": "Chat updated"},
        401: {"description": "Not authenticated"},
        404: {"description": "Chat not found"}
    })
async def update_chat(
    chat_id: str,
    chat_data: ChatUpdate,
    current_user: UserResponse = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Update chat details such as title.
    """
    chat = await chat_service.update_chat(chat_id, current_user.id, chat_data)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatResponse(**chat)

@router.delete("/{chat_id}",
    description="Delete a chat",
    responses={
        200: {"description": "Chat deleted"},
        401: {"description": "Not authenticated"},
        404: {"description": "Chat not found"}
    })
async def delete_chat(
    chat_id: str,
    current_user: UserResponse = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Delete a chat and all its messages.
    """
    success = await chat_service.delete_chat(chat_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"detail": "Chat deleted successfully"}

@router.post("/stream",
    description="Stream a chat response",
    responses={
        200: {"description": "Streaming response"},
        401: {"description": "Not authenticated"}
    })
async def stream_chat(
    request: StreamRequest,
    current_user: UserResponse = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Stream a chat response for the given message.
    If chat_id is provided, adds to an existing chat, otherwise creates a new one.
    Returns a streaming response with chunks of text as they're generated.
    """
    async def event_generator():
        async for chunk in chat_service.stream_chat_response(
            request.message, 
            request.chat_id, 
            current_user.id
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    ) 