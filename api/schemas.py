from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Question utilisateur")


class AskResponse(BaseModel):
    question: str
    answer: str
    route_used: str
    sql_success: bool