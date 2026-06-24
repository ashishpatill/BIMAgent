import re

def classify_query(query: str) -> str:
    query_lower = query.lower()
    if any(k in query_lower for k in ["hippo", "graph", "relation", "connect", "path"]):
        return "graph"
    elif any(k in query_lower for k in ["tree", "walk", "page", "document", "hierarchy"]):
        return "page_tree"
    elif any(k in query_lower for k in ["lookup", "keyword", "exact", "find"]):
        return "sparse"
    else:
        return "dense"

def router_node(state):
    """
    Classifies the query complexity and decides the retrieval route.
    """
    query = state.get("query", "")
    route = classify_query(query)
    trace = state.get("trace", [])
    trace.append(f"Router routed query to: {route}")
    return {"route": route, "trace": trace}
