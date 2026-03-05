from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import get_settings
import operator

settings = get_settings()


# ─── State shared across all agents ───────────────────────────────────────────

class AgentState(TypedDict):
    user_prompt: str
    generated_code: str
    test_code: str
    review: str
    messages: Annotated[Sequence[str], operator.add]


# ─── LLM setup ────────────────────────────────────────────────────────────────

def get_llm():
    return ChatGroq(
        api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
        streaming=True,
    )


# ─── Agent 1: Code Generator ──────────────────────────────────────────────────

def code_generator_node(state: AgentState) -> AgentState:
    llm = get_llm()
    messages = [
        SystemMessage(content="""You are an expert Python developer. 
Your job is to write clean, well-structured, production-ready Python code.
- Always include docstrings
- Use type hints
- Handle edge cases
- Write clean, readable code
Return ONLY the Python code block, no explanations outside the code."""),
        HumanMessage(content=f"Write Python code for the following requirement:\n\n{state['user_prompt']}")
    ]
    response = llm.invoke(messages)
    return {
        **state,
        "generated_code": response.content,
        "messages": [f"[CodeGenerator] Completed code generation"]
    }


# ─── Agent 2: Test Writer ──────────────────────────────────────────────────────

def test_writer_node(state: AgentState) -> AgentState:
    llm = get_llm()
    messages = [
        SystemMessage(content="""You are an expert Python test engineer.
Your job is to write comprehensive pytest unit tests.
- Cover happy path, edge cases, and error cases
- Use pytest fixtures where appropriate
- Use descriptive test names
- Add brief comments explaining what each test checks
Return ONLY the Python test code block, no explanations outside the code."""),
        HumanMessage(content=f"""Write pytest unit tests for this code:

{state['generated_code']}

Original requirement: {state['user_prompt']}""")
    ]
    response = llm.invoke(messages)
    return {
        **state,
        "test_code": response.content,
        "messages": [f"[TestWriter] Completed test generation"]
    }


# ─── Agent 3: Code Reviewer ───────────────────────────────────────────────────

def code_reviewer_node(state: AgentState) -> AgentState:
    llm = get_llm()
    messages = [
        SystemMessage(content="""You are a senior Python code reviewer.
Your job is to review code and tests thoroughly.
Provide your review in this exact format:

## Code Quality Score: X/10

## Strengths
- List 2-3 things done well

## Issues Found
- List any bugs, anti-patterns, or improvements needed

## Security Concerns
- List any security issues (or "None found")

## Performance Notes
- List any performance observations

## Final Verdict
One sentence summary and whether it's production-ready."""),
        HumanMessage(content=f"""Review this code and its tests:

### Original Requirement:
{state['user_prompt']}

### Generated Code:
{state['generated_code']}

### Tests:
{state['test_code']}""")
    ]
    response = llm.invoke(messages)
    return {
        **state,
        "review": response.content,
        "messages": [f"[CodeReviewer] Completed code review"]
    }


# ─── Build the LangGraph pipeline ─────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("code_generator", code_generator_node)
    workflow.add_node("test_writer", test_writer_node)
    workflow.add_node("code_reviewer", code_reviewer_node)

    workflow.set_entry_point("code_generator")
    workflow.add_edge("code_generator", "test_writer")
    workflow.add_edge("test_writer", "code_reviewer")
    workflow.add_edge("code_reviewer", END)

    return workflow.compile()


# Singleton pipeline
pipeline = build_pipeline()