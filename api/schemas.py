from pydantic import BaseModel
from typing import Optional, List

class KYCRequest(BaseModel):
    entity_name: str
    entity_type: str                    # "individual" | "corporate"
    jurisdiction: str                   # ISO 2-letter country code
    registration_number: Optional[str] = None
    date_of_birth: Optional[str]       = None
    aliases: Optional[List[str]]       = []
    include_transaction_analysis: bool = True

class KYCResponse(BaseModel):
    report_id: str
    status: str

class StatusResponse(BaseModel):
    report_id: str
    status: str                         # processing | completed | error | not_found
