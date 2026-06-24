import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

class GradeDoc(BaseModel):
    binary_score: str = Field(description="Relevance score 'yes' or 'no'")

def grade_document(query: str, doc_content: str) -> str:
    """
    Evaluates retrieved chunk against the query.
    Returns 'correct' (relevant), 'incorrect' (irrelevant), or 'ambiguous'.
    """
    query_lower = query.lower()
    doc_lower = doc_content.lower()
    
    # Deterministic heuristics for testing and fallback
    query_words = set(query_lower.split())
    doc_words = set(doc_lower.split())
    overlap = len(query_words.intersection(doc_words))
    
    if overlap >= 3:
        return "correct"
    elif overlap == 0:
        return "incorrect"
        
    # Attempt LLM grading if API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and api_key != "your_key_here":
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
            structured_llm = llm.with_structured_output(GradeDoc)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a grader assessing relevance of a retrieved document to a user query. "
                           "Respond with JSON containing 'binary_score' which must be 'yes' or 'no'."),
                ("human", f"Retrieved document: \n\n {doc_content} \n\n User query: {query}")
            ])
            
            chain = prompt | structured_llm
            result = chain.invoke({})
            if result.binary_score.lower() == "yes":
                return "correct"
            else:
                return "incorrect"
        except Exception:
            pass
            
    return "ambiguous"
