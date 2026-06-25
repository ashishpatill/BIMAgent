from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from store import get_vectorstore
from app.orchestrator.nodes.router import router_node
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.compression import compress_context
from app.agents.crag_grader import grade_document
from app.agents.generator import generate_answer

class GraphState(TypedDict):
    query: str
    route: str
    documents: List[dict]
    filtered_documents: List[dict]
    generation: str
    trace: List[str]
    has_fallback: bool

async def retrieve_node(state: GraphState):
    query = state["query"]
    route = state["route"]
    trace = state.get("trace", [])
    trace.append(f"Starting retrieval for route: {route}")
    
    vs = get_vectorstore()
    retrieved_docs = []
    try:
        docs_with_scores = vs.similarity_search_with_relevance_scores(query, k=5)
        retrieved_docs = [
            {
                "id": doc.metadata.get("source", doc.metadata.get("id", str(i))),
                "content": doc.page_content,
                "score": score,
            }
            for i, (doc, score) in enumerate(docs_with_scores)
        ]
    except Exception as e:
        trace.append(f"Qdrant retrieval failed: {e}")
        
    trace.append(f"Retrieved {len(retrieved_docs)} documents from Qdrant.")
    return {"documents": retrieved_docs, "trace": trace}

async def grade_node(state: GraphState):
    query = state["query"]
    docs = state["documents"]
    trace = state.get("trace", [])
    trace.append("Starting CRAG grading process.")
    
    filtered_docs = []
    for doc in docs:
        grade = grade_document(query, doc["content"])
        trace.append(f"Graded document {doc.get('id')}: {grade}")
        if grade in ["correct", "ambiguous"]:
            filtered_docs.append(doc)
            
    has_fallback = len(filtered_docs) == 0
    if has_fallback:
        trace.append("All retrieved documents graded as incorrect. Triggering fallback.")
        
    return {
        "filtered_documents": filtered_docs,
        "trace": trace,
        "has_fallback": has_fallback
    }

async def generate_node(state: GraphState):
    query = state["query"]
    docs = state["filtered_documents"]
    trace = state.get("trace", [])
    
    compressed_docs = compress_context(query, docs)
    trace.append("Compressed retrieved context.")
    
    generation = generate_answer(query, compressed_docs)
    trace.append("Generated final response.")
    return {"generation": generation, "trace": trace}

async def fallback_node(state: GraphState):
    trace = state.get("trace", [])
    trace.append("Initiating web search / fallback generation.")
    fallback_doc = {
        "id": "web_fallback",
        "content": f"Web search results for: {state['query']}. Scaling laws and adaptive RAG are state-of-the-art retrieval methods."
    }
    generation = generate_answer(state["query"], [fallback_doc])
    return {"generation": generation, "trace": trace}

def decide_to_generate(state: GraphState):
    if state.get("has_fallback", False):
        return "fallback"
    return "generate"

# Build the LangGraph workflow
workflow = StateGraph(GraphState)

workflow.add_node("router", router_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade", grade_node)
workflow.add_node("generate", generate_node)
workflow.add_node("fallback", fallback_node)

workflow.add_edge(START, "router")
workflow.add_edge("router", "retrieve")
workflow.add_edge("retrieve", "grade")

workflow.add_conditional_edges(
    "grade",
    decide_to_generate,
    {
        "fallback": "fallback",
        "generate": "generate"
    }
)

workflow.add_edge("fallback", END)
workflow.add_edge("generate", END)

app = workflow.compile()

async def run_workflow(query: str) -> dict:
    initial_state = {
        "query": query,
        "route": "",
        "documents": [],
        "filtered_documents": [],
        "generation": "",
        "trace": [],
        "has_fallback": False
    }
    return await app.ainvoke(initial_state)
