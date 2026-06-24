from app.orchestrator.nodes.router import classify_query

def test_classify_query_graph():
    assert classify_query("Find the path HippoRAG graph connection") == "graph"

def test_classify_query_tree():
    assert classify_query("Navigate the document page tree hierarchy") == "page_tree"

def test_classify_query_sparse():
    assert classify_query("lookup exact keyword match") == "sparse"

def test_classify_query_dense():
    assert classify_query("Standard deep learning embeddings RAG") == "dense"
