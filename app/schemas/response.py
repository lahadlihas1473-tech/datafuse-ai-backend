
from typing import Any, Optional

from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    details: str


class APIResponse(BaseModel):
    success: bool
    status: int
    message: str
    data: Optional[Any] = None
    error: Optional[APIError] = None

