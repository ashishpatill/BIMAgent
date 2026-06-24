def reciprocal_rank_fusion(results_list: list[list[dict]], k: int = 60) -> list[dict]:
    """
    Applies Reciprocal Rank Fusion (RRF) on multiple retrieved document lists.
    Each document dict should have a unique 'id' or 'content' key.
    """
    fused_scores = {}
    doc_map = {}
    
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc.get("id") or str(hash(doc.get("content", "")))
            doc_map[doc_id] = doc
            
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0.0
            
            fused_scores[doc_id] += 1.0 / (k + (rank + 1))
            
    sorted_docs = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    
    final_docs = []
    for doc_id, score in sorted_docs:
        doc = doc_map[doc_id].copy()
        doc["rrf_score"] = score
        final_docs.append(doc)
        
    return final_docs
