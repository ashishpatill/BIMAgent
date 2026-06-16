from enum import Enum
from typing import Optional, List
from pydantic import BaseModel

class CorpusType(str, Enum):
    CODE = "code"
    RESEARCH = "research"
    FINANCE = "finance"
    RESUME = "resume"

class BaseChunkMetadata(BaseModel):
    corpus: CorpusType
    source: str
    filename: str
    chunk_kind: str = "text"

# We can add more specific metadata here later if needed
# For now, we keep it flat and simple
class CodeMetadata(BaseChunkMetadata):
    repo: Optional[str] = None
    language: Optional[str] = None
    symbol: Optional[str] = None

class ResumeMetadata(BaseChunkMetadata):
    candidate_id: Optional[str] = None

class CandidateProfile(BaseModel):
    name: str
    email: Optional[str] = None
    skills: List[str] = []
    years_experience: float = 0.0
    companies: List[str] = []
    education: List[str] = []
    certifications: List[str] = []

class DocumentChunk(BaseModel):
    text: str
    metadata: dict
