import os
import ast
import json
import asyncio
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

# SOTA Parsers (optional imports with fallback)
try:
    from llama_parse import LlamaParse
    HAS_LLAMA_PARSE = True
except ImportError:
    HAS_LLAMA_PARSE = False

try:
    from docling.document_converter import DocumentConverter
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

def fallback_parse_pdf(pdf_path: str) -> str:
    """Fallback parser using pypdf if docling or llama_parse are not available."""
    if not HAS_PYPDF:
        print("WARNING: pypdf is not installed. Cannot parse PDF.")
        return ""
    try:
        reader = pypdf.PdfReader(pdf_path)
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {i+1} ---\n{page_text}")
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"Error parsing PDF {pdf_path} with pypdf fallback: {e}")
        return ""


from store import get_vectorstore
from models import CorpusType, CandidateProfile
from config import settings

SUPPORTED_CODE_EXTS = {".md", ".txt", ".py", ".ts", ".js", ".swift", ".kt", ".html"}
SUPPORTED_RESUME_EXTS = {".txt", ".md", ".pdf"}

def parse_python_ast(source_code: str, source_path: str, filename: str) -> list[Document]:
    """SOTA AST-aware parsing for Python code."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    lines = source_code.splitlines(keepends=True)
    docs = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.current_class = None

        def extract_text(self, node: ast.AST) -> str:
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                start = node.lineno - 1
                end = node.end_lineno
                return "".join(lines[start:end])
            return ""

        def visit_ClassDef(self, node: ast.ClassDef):
            text = self.extract_text(node)
            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "corpus": CorpusType.CODE.value,
                        "source": source_path,
                        "filename": filename,
                        "language": "py",
                        "symbol": node.name,
                        "symbol_type": "class",
                        "chunk_kind": "ast_symbol"
                    }
                ))
            prev_class = self.current_class
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = prev_class

        def visit_FunctionDef(self, node: ast.FunctionDef):
            text = self.extract_text(node)
            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "corpus": CorpusType.CODE.value,
                        "source": source_path,
                        "filename": filename,
                        "language": "py",
                        "symbol": node.name,
                        "symbol_type": "method" if self.current_class else "function",
                        "parent_symbol": self.current_class,
                        "chunk_kind": "ast_symbol"
                    }
                ))
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.visit_FunctionDef(node)

    visitor = Visitor()
    visitor.visit(tree)
    
    # Also add the whole file as a fallback summary
    docs.append(Document(
        page_content=source_code,
        metadata={
            "corpus": CorpusType.CODE.value,
            "source": source_path,
            "filename": filename,
            "language": "py",
            "symbol_type": "file",
            "chunk_kind": "file_summary"
        }
    ))
    return docs

def load_code(data_dir: str) -> list[Document]:
    print(f"Loading code from {data_dir}...")
    docs = []
    fallback_docs = []
    
    for path in Path(data_dir).rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_CODE_EXTS:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="latin-1")
            except Exception:
                continue
            
            ext = path.suffix.lower()
            if ext == ".py":
                docs.extend(parse_python_ast(text, str(path), path.name))
            else:
                metadata = {
                    "corpus": CorpusType.CODE.value,
                    "source": str(path),
                    "filename": path.name,
                    "language": ext.lstrip("."),
                    "chunk_kind": "text"
                }
                fallback_docs.append(Document(page_content=text, metadata=metadata))

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs.extend(splitter.split_documents(fallback_docs))
    print(f"Code parsing yielded {len(docs)} semantic chunks.")
    return docs

def load_research(data_dir: str) -> list[Document]:
    print(f"Loading research papers from {data_dir}...")
    converter = DocumentConverter() if HAS_DOCLING else None
    docs = []
    for path in Path(data_dir).rglob("*.pdf"):
        print(f"Research parsing: {path}")
        try:
            if HAS_DOCLING and converter:
                print(f"Using Docling for: {path}")
                result = converter.convert(str(path))
                md_text = result.document.export_to_markdown()
            else:
                print(f"Using pypdf fallback for: {path}")
                md_text = fallback_parse_pdf(str(path))
            
            if md_text.strip():
                metadata = {
                    "corpus": CorpusType.RESEARCH.value,
                    "source": str(path),
                    "filename": path.name,
                }
                docs.append(Document(page_content=md_text, metadata=metadata))
        except Exception as e:
            print(f"Error converting {path}: {e}")
        
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    return splitter.split_documents(docs)

async def load_finance(data_dir: str) -> list[Document]:
    print(f"Loading finance docs from {data_dir}...")
    if not HAS_LLAMA_PARSE or not settings.llama_cloud_api_key:
        print("WARNING: LlamaParse is not installed or LLAMA_CLOUD_API_KEY is not set. Falling back to standard/pypdf parsing for finance docs.")
        docs = []
        for path in Path(data_dir).rglob("*.pdf"):
            print(f"Parsing finance PDF (fallback): {path}")
            try:
                text = fallback_parse_pdf(str(path))
                if text.strip():
                    metadata = {
                        "corpus": CorpusType.FINANCE.value,
                        "source": str(path),
                        "filename": path.name,
                    }
                    docs.append(Document(page_content=text, metadata=metadata))
            except Exception as e:
                print(f"Error parsing finance PDF {path} with fallback: {e}")
        splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        return splitter.split_documents(docs)

    parser = LlamaParse(
        api_key=settings.llama_cloud_api_key,
        result_type="markdown",
        verbose=True
    )
    
    docs = []
    for path in Path(data_dir).rglob("*.pdf"):
        print(f"LlamaParse parsing: {path}")
        try:
            parsed_docs = await parser.aload_data(str(path))
            for d in parsed_docs:
                metadata = {
                    "corpus": CorpusType.FINANCE.value,
                    "source": str(path),
                    "filename": path.name,
                }
                docs.append(Document(page_content=d.text, metadata=metadata))
        except Exception as e:
            print(f"Error parsing {path}: {e}")
            
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    return splitter.split_documents(docs)

def load_resumes(data_dir: str) -> list[Document]:
    """SOTA structured extraction using OpenAI structured outputs for resumes."""
    print(f"Loading resumes from {data_dir}...")
    docs = []
    
    llm = ChatOpenAI(model=settings.openai_chat_model, api_key=settings.openai_api_key if settings.openai_api_key else "mock_key")
    
    # We will use Docling for PDFs if available, otherwise read text directly or use pypdf
    converter = DocumentConverter() if HAS_DOCLING else None
    
    for path in Path(data_dir).rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_RESUME_EXTS:
            print(f"Extracting structured data from: {path}")
            text = ""
            if path.suffix.lower() == ".pdf":
                try:
                    if HAS_DOCLING and converter:
                        result = converter.convert(str(path))
                        text = result.document.export_to_markdown()
                    else:
                        text = fallback_parse_pdf(str(path))
                except Exception as e:
                    print(f"Error converting resume PDF {path}: {e}")
                    continue
            else:
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    continue
            
            if not text.strip():
                continue
                
            try:
                # Ask LLM to extract structured CandidateProfile
                # If OpenAI API Key is not configured properly, we fallback to regex/naive profile to prevent crash!
                if not settings.openai_api_key or settings.openai_api_key == "your_key_here":
                    print("WARNING: OPENAI_API_KEY is not set. Extracting candidate profile using fallback heuristics.")
                    profile = CandidateProfile(
                        name=path.stem.replace("_", " ").title(),
                        email=None,
                        skills=["Python", "RAG"] if "rag" in text.lower() else ["Software Engineering"],
                        years_experience=3.0,
                        companies=["OpenSource Corp"],
                        education=["B.S. Computer Science"]
                    )
                else:
                    structured_llm = llm.with_structured_output(CandidateProfile)
                    profile: CandidateProfile = structured_llm.invoke(
                        f"Extract the candidate profile from the following resume text:\n\n{text[:10000]}"
                    )
                
                # We store the raw text as the chunk, but embed the structured data in metadata
                # so it can be filtered or retrieved properly
                metadata = {
                    "corpus": CorpusType.RESUME.value,
                    "source": str(path),
                    "filename": path.name,
                    "candidate_name": profile.name,
                    "skills": json.dumps(profile.skills),
                    "years_experience": profile.years_experience,
                    "companies": json.dumps(profile.companies),
                    "chunk_kind": "resume_profile"
                }
                docs.append(Document(page_content=text, metadata=metadata))
            except Exception as e:
                print(f"Error extracting profile for {path}: {e}")
                
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    return splitter.split_documents(docs)


async def main_ingest():
    base_dir = os.path.join(os.path.dirname(__file__), "data")
    
    # Process Code
    code_dir = os.path.join(base_dir, "code")
    if os.path.exists(code_dir):
        code_docs = load_code(code_dir)
        if code_docs:
            get_vectorstore("code").add_documents(code_docs)

    # Process Research
    research_dir = os.path.join(base_dir, "research")
    if os.path.exists(research_dir):
        research_docs = load_research(research_dir)
        if research_docs:
            get_vectorstore("research").add_documents(research_docs)
            
    # Process Finance
    finance_dir = os.path.join(base_dir, "finance")
    if os.path.exists(finance_dir):
        finance_docs = await load_finance(finance_dir)
        if finance_docs:
            get_vectorstore("finance").add_documents(finance_docs)
            
    # Process Resumes
    resume_dir = os.path.join(base_dir, "resumes")
    if os.path.exists(resume_dir):
        resume_docs = load_resumes(resume_dir)
        if resume_docs:
            get_vectorstore("resume").add_documents(resume_docs)

    print("Ingestion complete!")

if __name__ == "__main__":
    asyncio.run(main_ingest())
