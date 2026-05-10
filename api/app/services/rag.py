import logging
from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.config import get_settings
from app.db.session import AsyncSessionFactory
from app.services.retrieval import retrieve_similar_chunks

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGState(TypedDict):
    messages: Annotated[list, add_messages]
    question: str
    retrieved_chunks: list[dict]
    not_found: bool


def _build_context_prompt(chunks: list[dict]) -> str:
    parts = [
        f"[Fonte: {c['filename']}, trecho {c['chunk_index']}]\n{c['content']}"
        for c in chunks
    ]
    context = "\n\n---\n\n".join(parts)
    return (
        "Você é o assistente de suporte técnico da Cancella Informática. "
        "Responda EXCLUSIVAMENTE com base nos manuais técnicos fornecidos abaixo. "
        "Se a informação não estiver nos manuais, informe que não encontrou a informação. "
        "Seja preciso, técnico e objetivo.\n\n"
        f"MANUAIS DISPONÍVEIS:\n{context}"
    )


async def setup_rag_graph():
    checkpointer = AsyncPostgresSaver.from_conn_string(settings.langgraph_conn_string)
    await checkpointer.setup()

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        streaming=True,
        temperature=0,
    )

    async def retrieve(state: RAGState) -> dict:
        async with AsyncSessionFactory() as session:
            chunks = await retrieve_similar_chunks(state["question"], session)
        return {"retrieved_chunks": chunks}

    async def hallucination_guard(state: RAGState) -> dict:
        if not state.get("retrieved_chunks"):
            return {"not_found": True}
        return {"not_found": False}

    def route_from_guard(state: RAGState) -> str:
        return END if state.get("not_found") else "generate"

    async def generate(state: RAGState) -> dict:
        system_content = _build_context_prompt(state["retrieved_chunks"])
        messages = [SystemMessage(content=system_content)] + list(state["messages"])
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(RAGState)
    builder.add_node("retrieve", retrieve)
    builder.add_node("hallucination_guard", hallucination_guard)
    builder.add_node("generate", generate)

    builder.set_entry_point("retrieve")
    builder.add_edge("retrieve", "hallucination_guard")
    builder.add_conditional_edges(
        "hallucination_guard",
        route_from_guard,
        {"generate": "generate", END: END},
    )
    builder.add_edge("generate", END)

    logger.info("RAG graph compiled with PostgresSaver checkpointer")
    return builder.compile(checkpointer=checkpointer)
