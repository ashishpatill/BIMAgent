import sys
import json
from typing import TypedDict, Annotated, Sequence
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from store import get_vectorstore
from models import CorpusType
from config import settings

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    query: str
    corpus: CorpusType
    context: str

def router_node(state: AgentState):
    """LLM or Rule-based router to decide the corpus."""
    print("--- ROUTER NODE ---")
    query = state["query"].lower()
    
    if any(term in query for term in ["revenue", "profit", "stock", "margin", "ebitda", "quarter"]):
        corpus = CorpusType.FINANCE
    elif any(term in query for term in ["candidate", "resume", "experience", "skill", "education"]):
        corpus = CorpusType.RESUME
    elif any(term in query for term in ["bug", "code", "function", "class", "repo", "implementation"]):
        corpus = CorpusType.CODE
    else:
        corpus = CorpusType.RESEARCH
        
    print(f"Routed query to: {corpus.value}")
    return {"corpus": corpus}

def retriever_node(state: AgentState):
    """Retrieves documents from the selected Qdrant corpus."""
    print("--- RETRIEVER NODE ---")
    corpus = state["corpus"]
    query = state["query"]
    
    vectorstore = get_vectorstore(collection_suffix=corpus.value)
    try:
        docs = vectorstore.similarity_search(query, k=5)
        
        # We format the context to include metadata which is crucial for SOTA RAG (e.g. knowing the symbol, candidate profile)
        context_parts = []
        for i, d in enumerate(docs):
            meta_str = json.dumps(d.metadata, indent=2)
            context_parts.append(f"--- Document {i+1} ---\nMetadata: {meta_str}\nContent:\n{d.page_content}")
            
        context = "\n\n".join(context_parts)
        print(f"Retrieved {len(docs)} documents.")
    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")
        context = ""
        
    return {"context": context}

def generator_node(state: AgentState):
    """Generates the final answer using the retrieved context."""
    print("--- GENERATOR NODE ---")
    context = state["context"]
    query = state["query"]
    
    if not context:
        return {"messages": [SystemMessage(content="No relevant documents found. Please ingest data first.")]}

    if not settings.openai_api_key or settings.openai_api_key == "your_key_here":
        print("WARNING: OPENAI_API_KEY is not set. Generating dry-run fallback response based on context.")
        from langchain_core.messages import AIMessage
        fallback_msg = f"[DRY-RUN MOCK ANSWER]\nRetrieved the following context chunks:\n\n{context[:600]}...\n\n(Note: To generate a SOTA LLM answer, please set your OPENAI_API_KEY in the .env file.)"
        return {"messages": [AIMessage(content=fallback_msg)]}

    llm = ChatOpenAI(model=settings.openai_chat_model, api_key=settings.openai_api_key)
    
    # We pass the metadata-enriched context to the LLM
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert SOTA RAG assistant. Use the retrieved context (which includes source metadata) to answer the user's question accurately. If the context contains metadata (like 'candidate_name', 'skills', 'symbol_type', 'company'), explicitly use it to provide a structured, high-quality answer.\n\nContext:\n{context}"),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"context": context, "question": query})
    
    return {"messages": [response]}


# Build the LangGraph
workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("generator", generator_node)

workflow.add_edge(START, "router")
workflow.add_edge("router", "retriever")
workflow.add_edge("retriever", "generator")
workflow.add_edge("generator", END)

app = workflow.compile()

def main(query: str):
    print(f"Starting LangGraph workflow for query: '{query}'\n")
    
    initial_state = {
        "query": query,
        "messages": [],
        "context": "",
        "corpus": CorpusType.CODE # default fallback
    }
    
    print("\n=== FINAL ANSWER ===\n")
    try:
        result = app.invoke(initial_state)
        print(result["messages"][-1].content)
    except Exception as e:
        print(f"Execution Error: {e}")
    print("\n====================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py 'your question here'")
    else:
        main(sys.argv[1])
