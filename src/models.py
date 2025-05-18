from typing import Optional, Any
from pydantic import BaseModel, Field

class AIConfigState(BaseModel):
    selected_ai_provider: str = "OpenRouter"
    selected_model_for_provider: Optional[str] = None

class Tab2State(BaseModel):
    selected_enquiry_id: Optional[Any] = None
    current_ai_suggestions: Optional[Any] = None
    current_ai_suggestions_id: Optional[Any] = None
    itinerary_loaded_for_tab2: Optional[Any] = None

class Tab3State(BaseModel):
    selected_enquiry_id: Optional[Any] = None
    enquiry_details: Optional[Any] = None
    client_name: str = "Valued Client"
    itinerary_info: Optional[Any] = None
    vendor_reply_info: Optional[Any] = None
    current_quotation_db_id: Optional[Any] = None
    current_pdf_storage_path: Optional[str] = None
    current_docx_storage_path: Optional[str] = None
    quotation_pdf_bytes: Optional[bytes] = None
    quotation_docx_bytes: Optional[bytes] = None
    show_quotation_success: bool = False
    cached_graph_output: Optional[Any] = None
    cache_key: Optional[str] = None

class AppSessionState(BaseModel):
    ai_config: AIConfigState = Field(default_factory=AIConfigState)
    tab2_state: Tab2State = Field(default_factory=Tab2State)
    tab3_state: Tab3State = Field(default_factory=Tab3State)
    operation_success_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
