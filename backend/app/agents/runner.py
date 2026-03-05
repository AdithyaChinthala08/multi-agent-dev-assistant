import asyncio
import traceback
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.streaming import manager
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.session import AgentSession, AgentRun
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

AGENTS = [
    {
        "key": "code_generator",
        "name": "Code Generator",
        "order": 1,
        "system": """You are an expert Python developer. 
Write clean, well-structured, production-ready Python code.
- Always include docstrings
- Use type hints  
- Handle edge cases
Return ONLY the Python code block, no explanations outside the code.""",
    },
    {
        "key": "test_writer",
        "name": "Test Writer",
        "order": 2,
        "system": """You are an expert Python test engineer.
Write comprehensive pytest unit tests.
- Cover happy path, edge cases, and error cases
- Use descriptive test names
Return ONLY the Python test code block.""",
    },
    {
        "key": "code_reviewer",
        "name": "Code Reviewer",
        "order": 3,
        "system": """You are a strict senior Python code reviewer at a top tech company.
Review code and tests honestly. Use this EXACT format:

## Code Quality Score: X/10

Score strictly using these criteria:
- 10/10: Production-perfect, nothing to improve
- 8-9/10: Good code, minor style or edge case issues only
- 6-7/10: Works but has real issues (missing error handling, inefficient algorithm, poor naming)
- 4-5/10: Multiple bugs, missing tests, bad practices
- 1-3/10: Broken or fundamentally flawed

Be HONEST. Most code has real issues. Do not default to 9/10.

## Strengths
- List 2-3 specific things done well

## Issues Found
- List ALL real bugs, missing edge cases, inefficiencies, bad practices
- Be specific with line-level feedback where possible

## Security Concerns
- List any real security issues, or "None found"

## Performance Analysis
- State the time and space complexity (e.g. O(n log n) time, O(n) space)
- Suggest better complexity if possible

## Final Verdict
One sentence: is it production-ready or not, and why.""",
    },
]


def get_streaming_llm():
    return ChatGroq(
        api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
        streaming=True,
    )


async def run_pipeline_streaming(session_id: str, user_prompt: str):
    """Run all 3 agents sequentially, streaming output to WebSocket."""
    context = {"user_prompt": user_prompt}

    async with AsyncSessionLocal() as db:
        # Mark session as running
        result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.status = "running"
            await db.commit()

    for agent_cfg in AGENTS:
        agent_key = agent_cfg["key"]
        agent_name = agent_cfg["name"]
        order = agent_cfg["order"]

        await manager.send_agent_start(session_id, agent_name, order)

        # Build prompt based on which agent
        if agent_key == "code_generator":
            user_msg = f"Write Python code for:\n\n{user_prompt}"
        elif agent_key == "test_writer":
            user_msg = f"""Write pytest tests for this code:

{context.get('generated_code', '')}

Original requirement: {user_prompt}"""
        else:  # code_reviewer
            user_msg = f"""Review this code and tests:

### Requirement:
{user_prompt}

### Code:
{context.get('generated_code', '')}

### Tests:
{context.get('test_code', '')}"""

        messages = [
            SystemMessage(content=agent_cfg["system"]),
            HumanMessage(content=user_msg),
        ]

        llm = get_streaming_llm()
        full_output = ""

        try:
            logger.info(f"Starting agent: {agent_name}")
            async for chunk in llm.astream(messages):
                text = chunk.content
                if text:
                    full_output += text
                    await manager.send_agent_chunk(session_id, agent_name, text)
                    await asyncio.sleep(0)  # yield control

            # Store in context
            if agent_key == "code_generator":
                context["generated_code"] = full_output
            elif agent_key == "test_writer":
                context["test_code"] = full_output
            else:
                context["review"] = full_output

            # Save to DB
            async with AsyncSessionLocal() as db:
                run = AgentRun(
                    session_id=session_id,
                    agent_name=agent_key,
                    agent_order=order,
                    output=full_output,
                    status="completed",
                )
                db.add(run)
                await db.commit()

            await manager.send_agent_done(session_id, agent_name, full_output)

        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"Agent {agent_name} failed: {error_detail}")
            await manager.send_error(session_id, f"{agent_name} failed: {str(e)}")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
                session = result.scalar_one_or_none()
                if session:
                    session.status = "failed"
                    await db.commit()
            return

    # Mark session complete
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.status = "completed"
            await db.commit()

    await manager.send_pipeline_complete(session_id)