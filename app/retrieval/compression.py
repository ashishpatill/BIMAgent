import re

def compress_context(query: str, documents: list[dict], max_tokens: int = 500) -> list[dict]:
    """
    Compresses document context by extracting the sentences most relevant to the query.
    This simulates token-span compression (PISCO) by pruning irrelevant sentences.
    """
    query_words = set(re.findall(r'\w+', query.lower()))
    if not query_words:
        return documents
        
    compressed_docs = []
    
    for doc in documents:
        content = doc.get("content", "")
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # Score sentences based on keyword overlap
        scored_sentences = []
        for idx, sentence in enumerate(sentences):
            words = set(re.findall(r'\w+', sentence.lower()))
            overlap = len(words.intersection(query_words))
            scored_sentences.append((idx, sentence, overlap))
            
        # Find the sentence with the highest overlap
        best_idx = -1
        best_score = -1
        for idx, _, score in scored_sentences:
            if score > best_score:
                best_score = score
                best_idx = idx
                
        if best_idx != -1 and best_score > 0:
            # Keep the best sentence and its surrounding context (1 sentence before and after)
            start = max(0, best_idx - 1)
            end = min(len(sentences), best_idx + 2)
            compressed_content = " ".join(sentences[start:end])
        else:
            # Default to the first two sentences if no overlap
            compressed_content = " ".join(sentences[:2])
            
        new_doc = doc.copy()
        new_doc["content"] = compressed_content
        new_doc["original_content"] = content
        new_doc["compressed"] = True
        compressed_docs.append(new_doc)
        
    return compressed_docs
