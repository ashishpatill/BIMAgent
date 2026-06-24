from app.retrieval.fusion import reciprocal_rank_fusion

def test_rrf_basic():
    results1 = [
        {"id": "doc1", "content": "hello world"},
        {"id": "doc2", "content": "foo bar"}
    ]
    results2 = [
        {"id": "doc2", "content": "foo bar"},
        {"id": "doc3", "content": "test content"}
    ]
    
    fused = reciprocal_rank_fusion([results1, results2], k=60)
    
    # Doc2 should rank first since it is present in both lists
    assert fused[0]["id"] == "doc2"
    assert len(fused) == 3
