from pydantic import BaseModel
from typing import List, Optional

class PageText(BaseModel):
    page_number: int
    text: str

class DocumentBase(BaseModel):
    id: str
    filename: str
    page_count: int
    word_count: int
    uploadedAt: str
    status: str
    demo_mode: bool = False

class DocumentDetail(DocumentBase):
    pages: List[PageText] = []

class UploadResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    word_count: int
    uploadedAt: str
    status: str
    demo_mode: bool
    pages: List[PageText]
