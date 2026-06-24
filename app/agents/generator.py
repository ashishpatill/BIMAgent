import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

def generate_answer(query: str, compressed_docs: list[dict]) -> str:
    """
    Generates the final answer using the fused and compressed context, ensuring citations are included.
    """
    if not compressed_docs:
        return "I do not have enough context to answer this query."

    context_parts = []
    for idx, doc in enumerate(compressed_docs):
        doc_id = doc.get("id") or f"doc_{idx}"
        context_parts.append(f"[{doc_id}]: {doc.get('content')}")
        
    context = "\n\n".join(context_parts)
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and api_key != "your_key_here":
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=api_key)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert RAG generator. Use the retrieved context to answer the user query. "
                           "You must include inline citations using the format [doc_id] where appropriate. "
                           "If the context is insufficient, state that you do not know."),
                ("human", f"Context: \n\n {context} \n\n Query: {query}")
            ])
            chain = prompt | llm
            response = chain.invoke({})
            return response.content
        except Exception as e:
            return f"Error during generation: {e}. Fallback to mock."
            
    # Fallback to mock generation for tests/dry-run
    best_doc = compressed_docs[0]
    best_id = best_doc.get("id") or "doc_0"
    return f"[MOCK ANSWER] Based on [{best_id}]: {best_doc.get('content')[:150]}"
