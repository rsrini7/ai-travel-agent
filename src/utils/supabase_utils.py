# supabase_utils.py
import os
from supabase import create_client, Client
from postgrest import APIError
from httpx import HTTPStatusError
from src.utils.constants import (
    TABLE_CLIENTS, TABLE_ENQUIRIES, TABLE_ITINERARIES,
    TABLE_VENDOR_REPLIES, TABLE_QUOTATIONS
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key not found in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def _format_error_message(e, context_message="Error"):
    if isinstance(e, APIError):
        error_details = f"Code: {e.code}, Message: {e.message}"
        if hasattr(e, 'details') and e.details: error_details += f", Details: {e.details}"
        if hasattr(e, 'hint') and e.hint: error_details += f", Hint: {e.hint}"
        print(f"{context_message}: APIError - {error_details}")
        return f"Database API Error: {e.message}"
    elif isinstance(e, HTTPStatusError):
        print(f"{context_message}: HTTP Status Error - Status: {e.response.status_code}, Response: {e.response.text}")
        return f"HTTP Error {e.response.status_code}: {e.response.reason_phrase}"
    else:
        print(f"{context_message}: Unexpected error - Type: {type(e)}, Error: {e}")
        return f"Unexpected error: {str(e)}"

def add_client(enquiry_id: str, name: str, mobile: str, city: str, email: str = None) -> tuple[dict, str]:
    try:
        client_data = supabase.table(TABLE_CLIENTS).insert({ # Use constant
            'enquiry_id': enquiry_id,
            'name': name,
            'mobile': mobile,
            'city': city,
            'email': email
        }).execute()
        if client_data.data:
            return client_data.data[0], None
        return None, "No data returned from Supabase for client add"
    except Exception as e:
        return None, str(e)

def add_enquiry(destination: str, num_days: int, traveler_count: int, trip_type: str):
    try:
        response = supabase.table(TABLE_ENQUIRIES).insert({ # Use constant
            "destination": destination,
            "num_days": num_days,
            "traveler_count": traveler_count,
            "trip_type": trip_type
        }).execute()
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding enquiry")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding enquiry")

def get_enquiries():
    try:
        response = supabase.table(TABLE_ENQUIRIES).select("*").order("created_at", desc=True).execute() # Use constant
        return response.data if response else [], None
    except (APIError, HTTPStatusError) as e:
        return [], _format_error_message(e, "Error fetching enquiries")
    except Exception as e:
        return [], _format_error_message(e, "Unexpected error fetching enquiries")

def get_enquiry_by_id(enquiry_id: str):
    try:
        response = supabase.table(TABLE_ENQUIRIES).select("*").eq("id", enquiry_id).single().execute() # Use constant
        return response.data if response else None, None
    except APIError as e:
        if "PGRST116" in str(e.message) or "Expected 1 row" in str(e.message):
            return None, None 
        return None, _format_error_message(e, f"Error fetching enquiry {enquiry_id}")
    except HTTPStatusError as e:
        return None, _format_error_message(e, f"HTTP error fetching enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching enquiry {enquiry_id}")

def get_client_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table(TABLE_CLIENTS).select("*").eq("enquiry_id", enquiry_id).limit(1).maybe_single().execute() # Use constant
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching client for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching client for enquiry {enquiry_id}")

def add_itinerary(enquiry_id: str, itinerary_text: str):
    try:
        response = supabase.table(TABLE_ITINERARIES).insert({ # Use constant
            "enquiry_id": enquiry_id,
            "itinerary_text": itinerary_text
        }).execute()
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding itinerary")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding itinerary")

def get_itinerary_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table(TABLE_ITINERARIES).select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute() # Use constant
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching itinerary for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching itinerary for enquiry {enquiry_id}")

def add_vendor_reply(enquiry_id: str, reply_text: str):
    try:
        response = supabase.table(TABLE_VENDOR_REPLIES).insert({ # Use constant
            "enquiry_id": enquiry_id,
            "reply_text": reply_text
        }).execute()
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding vendor reply")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding vendor reply")

def get_vendor_reply_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table(TABLE_VENDOR_REPLIES).select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute() # Use constant
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching vendor reply for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching vendor reply for enquiry {enquiry_id}")

def upload_file_to_storage(bucket_name: str, file_path_in_storage: str, file_bytes: bytes, content_type: str) -> tuple[str | None, str | None]:
    try:
        response = supabase.storage.from_(bucket_name).upload( # bucket_name is already a parameter
            path=file_path_in_storage,
            file=file_bytes,
            file_options={"content-type": content_type, "cache-control": "3600", "upsert": "true"}
        )
        print(f"Storage upload response: {response}") 
        return file_path_in_storage, None
    except APIError as e:
        return None, _format_error_message(e, f"Supabase API Error uploading to storage bucket '{bucket_name}'")
    except HTTPStatusError as e:
         return None, _format_error_message(e, f"HTTP Error uploading to storage bucket '{bucket_name}'")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error uploading to storage bucket '{bucket_name}'")

def add_quotation(
    enquiry_id: str,
    structured_data_json: dict,
    itinerary_used_id: str = None,
    vendor_reply_used_id: str = None,
    pdf_storage_path: str = None,
    docx_storage_path: str = None
):
    insert_data = {
        "enquiry_id": enquiry_id,
        "structured_data_json": structured_data_json
    }
    if itinerary_used_id: insert_data["itinerary_used_id"] = itinerary_used_id
    if vendor_reply_used_id: insert_data["vendor_reply_used_id"] = vendor_reply_used_id
    if pdf_storage_path: insert_data["pdf_storage_path"] = pdf_storage_path
    if docx_storage_path: insert_data["docx_storage_path"] = docx_storage_path

    try:
        response = supabase.table(TABLE_QUOTATIONS).insert(insert_data).execute() # Use constant
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding quotation record")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding quotation record")

def update_quotation_storage_path(quotation_id: str, field_name: str, storage_path: str):
    if field_name not in ['pdf_storage_path', 'docx_storage_path']:
        return None, "Invalid field name for updating storage path."
    try:
        response = supabase.table(TABLE_QUOTATIONS).update({field_name: storage_path}).eq("id", quotation_id).execute() # Use constant
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error updating {field_name} for quotation {quotation_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error updating {field_name} for quotation {quotation_id}")

def get_quotation_by_enquiry_id(enquiry_id: str): 
    try:
        response = supabase.table(TABLE_QUOTATIONS).select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute() # Use constant
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching quotation for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching quotation for enquiry {enquiry_id}")

def get_public_url(bucket_name: str, file_path: str) -> str | None:
    if not file_path: return None
    try:
        url_response = supabase.storage.from_(bucket_name).get_public_url(file_path) # bucket_name is parameter
        return url_response
    except Exception as e:
        print(f"Error generating public URL for {file_path} in {bucket_name}: {e}")
        return None

def create_signed_url(bucket_name: str, file_path: str, expires_in: int = 3600) -> tuple[str | None, str | None]:
    if not file_path: return None, "File path is empty"
    try:
        response = supabase.storage.from_(bucket_name).create_signed_url(file_path, expires_in) # bucket_name is parameter
        return response.get('signedURL'), None
    except Exception as e:
        print(f"Error generating signed URL for {file_path} in {bucket_name}: {e}")
        return None, str(e)