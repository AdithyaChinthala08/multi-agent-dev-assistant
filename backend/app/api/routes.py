from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid
import traceback

from app.core.database import get_db
from app.models.session import AgentSession, AgentRun
from app.agents.streaming import manager
from app.agents.runner import run_pipeline_streaming

router = APIRouter()


class CreateSessionRequest(BaseModel):
    prompt: str


class SessionResponse(BaseModel):
    session_id: str
    status: str
    prompt: str


@router.post("/sessions", response_model=SessionResponse)
async def create_session(body: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    session = AgentSession(
        id=str(uuid.uuid4()),
        user_prompt=body.prompt.strip(),
        status="pending",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse(session_id=session.id, status=session.status, prompt=session.user_prompt)


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentSession).order_by(AgentSession.created_at.desc()).limit(20)
    )
    sessions = result.scalars().all()
    return [{"session_id": s.id, "status": s.status, "prompt": s.user_prompt, "created_at": str(s.created_at)} for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    runs_result = await db.execute(
        select(AgentRun).where(AgentRun.session_id == session_id).order_by(AgentRun.agent_order)
    )
    runs = runs_result.scalars().all()
    return {
        "session_id": session.id,
        "status": session.status,
        "prompt": session.user_prompt,
        "created_at": str(session.created_at),
        "agents": [{"agent_name": r.agent_name, "order": r.agent_order, "output": r.output, "status": r.status} for r in runs],
    }


# ─── WebSocket — prompt passed as query param, no receive needed ──────────────

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    prompt: str = Query(...),
):
    print(f"[WS] New connection — session={session_id} prompt='{prompt[:80]}'")
    await manager.connect(session_id, websocket)
    try:
        await run_pipeline_streaming(session_id, prompt)
    except WebSocketDisconnect:
        print(f"[WS] Disconnected: {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        print(f"[WS] Error:\n{traceback.format_exc()}")
        try:
            await manager.send_error(session_id, str(e))
        except Exception:
            pass
        manager.disconnect(session_id)