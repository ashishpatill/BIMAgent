from app.agents.crag_grader import grade_document

def test_crag_correct():
    # At least 3 matching words should be correct
    query = "scaling laws RAG capacity"
    content = "RAG scaling laws indicate that capacity is important."
    assert grade_document(query, content) == "correct"

def test_crag_incorrect():
    # Zero overlapping words should yield incorrect
    query = "scaling laws"
    content = "completely different topic about apples and oranges."
    assert grade_document(query, content) == "incorrect"

def test_crag_ambiguous():
    # Small overlap should yield ambiguous
    query = "RAG scaling laws"
    content = "RAG capacity is important."
    assert grade_document(query, content) == "ambiguous"
