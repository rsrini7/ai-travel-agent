# supabase_utils.py
import os
from supabase import create_client, Client
from postgrest import APIError
from httpx import HTTPStatusError

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # This is likely your anon key

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key not found in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Existing functions (add_client, _format_error_message, add_enquiry, etc.) ---
# ... (keep all your existing functions from your previous supabase_utils.py)

def add_client(enquiry_id: str, name: str, mobile: str, city: str, email: str = None) -> tuple[dict, str]:
    try:
        client_data = supabase.table('clients').insert({
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


def add_enquiry(destination: str, num_days: int, traveler_count: int, trip_type: str):
    try:
        response = supabase.table("enquiries").insert({
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
        response = supabase.table("enquiries").select("*").order("created_at", desc=True).execute()
        return response.data if response else [], None
    except (APIError, HTTPStatusError) as e:
        return [], _format_error_message(e, "Error fetching enquiries")
    except Exception as e:
        return [], _format_error_message(e, "Unexpected error fetching enquiries")


def get_enquiry_by_id(enquiry_id: str):
    try:
        response = supabase.table("enquiries").select("*").eq("id", enquiry_id).single().execute()
        return response.data if response else None, None
    except APIError as e:
        if "PGRST116" in str(e.message) or "Expected 1 row" in str(e.message): # PGRST116: "Query result returned zero rows"
            return None, None # Not found is not an error in this context
        return None, _format_error_message(e, f"Error fetching enquiry {enquiry_id}")
    except HTTPStatusError as e:
        return None, _format_error_message(e, f"HTTP error fetching enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching enquiry {enquiry_id}")

def get_client_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table("clients").select("*").eq("enquiry_id", enquiry_id).limit(1).maybe_single().execute()
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching client for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching client for enquiry {enquiry_id}")

def add_itinerary(enquiry_id: str, itinerary_text: str):
    try:
        response = supabase.table("itineraries").insert({
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
        response = supabase.table("itineraries").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching itinerary for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching itinerary for enquiry {enquiry_id}")


def add_vendor_reply(enquiry_id: str, reply_text: str):
    try:
        response = supabase.table("vendor_replies").insert({
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
        response = supabase.table("vendor_replies").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching vendor reply for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching vendor reply for enquiry {enquiry_id}")

# --- NEW Storage Function ---
def upload_file_to_storage(bucket_name: str, file_path_in_storage: str, file_bytes: bytes, content_type: str) -> tuple[str | None, str | None]:
    """
    Uploads a file (as bytes) to Supabase Storage.

    Args:
        bucket_name: The name of the Supabase bucket.
        file_path_in_storage: The desired path and filename within the bucket.
        file_bytes: The file content as bytes.
        content_type: The MIME type of the file (e.g., "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document").

    Returns:
        tuple: (storage_path, error_message)
               storage_path is the path in storage if successful, else None.
               error_message is None if successful, else an error string.
    """
    try:
        # The supabase-py client's upload method returns the { 'path': 'file_path_in_storage' } on success
        # but it might raise an error for failures.
        # For consistency with other functions, we check for the key.
        response = supabase.storage.from_(bucket_name).upload(
            path=file_path_in_storage,
            file=file_bytes,
            file_options={"content-type": content_type, "cache-control": "3600", "upsert": "true"} # upsert true will overwrite if file exists
        )
        # Successful upload typically doesn't return data in `response.data` for storage like table ops.
        # The path is confirmed by lack of error and the input `file_path_in_storage`.
        # Supabase storage upload response is {'path': 'actual_path_key_if_different_or_same'}
        # or it directly returns the path key, or raises an error.
        # Let's assume it raises error on fail. If it returns a dict, we need to extract 'path'.
        # Based on common patterns, if no error, the path used for upload is the key.
        print(f"Storage upload response: {response}") # Log the response to understand its structure
        return file_path_in_storage, None
    except APIError as e: # Supabase specific API errors
        return None, _format_error_message(e, f"Supabase API Error uploading to storage bucket '{bucket_name}'")
    except HTTPStatusError as e: # HTTP errors
         return None, _format_error_message(e, f"HTTP Error uploading to storage bucket '{bucket_name}'")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error uploading to storage bucket '{bucket_name}'")


# --- MODIFIED Quotation Functions ---
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
    if itinerary_used_id:
        insert_data["itinerary_used_id"] = itinerary_used_id
    if vendor_reply_used_id:
        insert_data["vendor_reply_used_id"] = vendor_reply_used_id
    if pdf_storage_path:
        insert_data["pdf_storage_path"] = pdf_storage_path
    if docx_storage_path:
        insert_data["docx_storage_path"] = docx_storage_path

    try:
        response = supabase.table("quotations").insert(insert_data).execute()
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding quotation record")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding quotation record")

def update_quotation_storage_path(quotation_id: str, field_name: str, storage_path: str):
    """
    Updates a specific storage path field for an existing quotation record.
    Args:
        quotation_id: The ID of the quotation record to update.
        field_name: The column name to update (e.g., 'pdf_storage_path' or 'docx_storage_path').
        storage_path: The new storage path.
    Returns:
        tuple: (updated_data, error_message)
    """
    if field_name not in ['pdf_storage_path', 'docx_storage_path']:
        return None, "Invalid field name for updating storage path."
    try:
        response = supabase.table("quotations").update({field_name: storage_path}).eq("id", quotation_id).execute()
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error updating {field_name} for quotation {quotation_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error updating {field_name} for quotation {quotation_id}")


def get_quotation_by_enquiry_id(enquiry_id: str): # Keep as is, will fetch paths if they exist
    try:
        # Fetch the latest quotation for the enquiry
        response = supabase.table("quotations").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching quotation for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching quotation for enquiry {enquiry_id}")

def get_public_url(bucket_name: str, file_path: str) -> str | None:
    """
    Generates a public URL for a file in Supabase storage.
    Only works if the bucket is public or the file has public access via RLS.
    """
    if not file_path: return None
    try:
        url_response = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return url_response
    except Exception as e:
        print(f"Error generating public URL for {file_path} in {bucket_name}: {e}")
        return None

def create_signed_url(bucket_name: str, file_path: str, expires_in: int = 3600) -> tuple[str | None, str | None]:
    """
    Generates a signed URL for a file in Supabase storage.
    """
    if not file_path: return None, "File path is empty"
    try:
        response = supabase.storage.from_(bucket_name).create_signed_url(file_path, expires_in)
        return response.get('signedURL'), None
    except Exception as e:
        print(f"Error generating signed URL for {file_path} in {bucket_name}: {e}")
        return None, str(e)