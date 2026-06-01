from pydantic import BaseModel, ValidationError
from typing import Optional
from models.job_search_params import JobFunction, RemoteType
import logging

logger = logging.getLogger(__name__)

class JobSearchQuery(BaseModel):
    response: str
    complete: bool
    keywords: str
    job_function: JobFunction
    salary_min: Optional[int] = None
    remote_type: Optional[RemoteType] = None
    location: Optional[str] = None

def validate_job_search_query(raw_text: str) -> bool:
    try:
        JobSearchQuery.model_validate_json(raw_text)
        return True
    except ValidationError:
        print(f"The following text was not valid: {raw_text}")
        return False

