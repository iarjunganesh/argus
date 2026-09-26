from pydantic import BaseModel


class KYCRequest(BaseModel):
    entity_name: str
    entity_type: str  # "individual" | "corporate"
    jurisdiction: str  # ISO 2-letter country code
    registration_number: str | None = None
    date_of_birth: str | None = None
    aliases: list[str] | None = []
    include_transaction_analysis: bool = True


class KYCResponse(BaseModel):
    report_id: str
    status: str


class StatusResponse(BaseModel):
    report_id: str
    status: str  # processing | completed | error | not_found
