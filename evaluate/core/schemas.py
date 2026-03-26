# evaluate/core/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional


class EvalSample(BaseModel):
    """
    Représente une question d'évaluation RAGAS.
    """
    id: int = Field(..., ge=1)
    question: str = Field(..., min_length=3)
    ground_truth: str = Field(..., min_length=3)
    category: str = Field(..., min_length=2)
    answerable: bool


class SearchResultMetadata(BaseModel):
    """
    Métadonnées associées à un chunk retourné par le vector store.
    """
    source: str = Field(..., min_length=1)
    filename: Optional[str] = None
    category: Optional[str] = None
    full_path: Optional[str] = None
    sheet: Optional[str] = None
    chunk_id_in_doc: Optional[int] = None
    start_index: Optional[int] = None


class SearchResult(BaseModel):
    """
    Représente un résultat de recherche retourné par le vector store.
    """
    score: float
    raw_score: Optional[float] = None
    text: str = Field(..., min_length=1)
    metadata: SearchResultMetadata


class RagPipelineOutput(BaseModel):
    """
    Représente la sortie complète du pipeline RAG pour une question.
    """
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    search_results: List[SearchResult]
    context_str: str
    final_prompt_for_llm: str
    messages_for_api: List[dict]