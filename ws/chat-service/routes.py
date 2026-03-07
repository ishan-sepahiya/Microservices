import uuid, json, logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import ChatMessage, ChatRoom, MessageOut, RoomResponse

logger = logging.getLogger("chat")
router = APIRouter(tags=["Chat"])

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}
    async def connect(self, room_id: str, ws: WebSocket):
        await ws.accept()
        self.rooms.setdefault(room_id, []).append(ws)
    def disconnect(self, room_id: str, ws: WebSocket):
        if room_id in self.rooms:
            try: self.rooms[room_id].remove(ws)
            except ValueError: pass
    async def broadcast(self, room_id: str, message: str):
        for ws in list(self.rooms.get(room_id, [])):
            try: await ws.send_text(message)
            except Exception: self.rooms[room_id].remove(ws)
    def count(self, room_id: str) -> int:
        return len(self.rooms.get(room_id, []))

manager = ConnectionManager()

@router.post("/rooms", response_model=RoomResponse, status_code=201)
async def create_room(name: str, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(ChatRoom).where(ChatRoom.name == name))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Room exists")
    room = ChatRoom(name=name)
    db.add(room); await db.flush(); await db.refresh(room)
    return room

@router.get("/rooms", response_model=list[RoomResponse])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChatRoom).where(ChatRoom.is_active == True))  # noqa
    return list(result.scalars().all())

@router.get("/rooms/{room_id}/messages", response_model=list[MessageOut])
async def get_messages(room_id: uuid.UUID, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChatMessage).where(ChatMessage.room_id == room_id).order_by(ChatMessage.created_at.desc()).limit(limit))
    return list(reversed(result.scalars().all()))

@router.websocket("/ws/chat/{room_id}")
async def ws_chat(room_id: str, ws: WebSocket, sender_id: str = "anonymous", db: AsyncSession = Depends(get_db)):
    """Connect: ws://host/ws/chat/{room_id}?sender_id=your_id | Send: {"content":"hello"}"""
    await manager.connect(room_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            content = data.get("content", "").strip()
            if not content: continue
            msg = ChatMessage(room_id=uuid.UUID(room_id), sender_id=sender_id, content=content)
            db.add(msg); await db.flush()
            await manager.broadcast(room_id, json.dumps({
                "id": str(msg.id), "room_id": room_id, "sender_id": sender_id,
                "content": content, "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_connections": manager.count(room_id),
            }))
    except WebSocketDisconnect:
        manager.disconnect(room_id, ws)
        await manager.broadcast(room_id, json.dumps({"system": f"{sender_id} left"}))
