# supabase_utils.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from postgrest import APIError  # For catching specific PostgREST errors
from httpx import HTTPStatusError # For catching general HTTP errors if they occur

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key not found in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Helper for formatting error messages ---
def _format_error_message(e, context_message="Error"):
    if isinstance(e, APIError):
        # APIError from postgrest-py has code, details, hint, message
        error_details = f"Code: {e.code}, Message: {e.message}"
        if e.details:
            error_details += f", Details: {e.details}"
        if e.hint:
            error_details += f", Hint: {e.hint}"
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
        # In supabase-py v2, if an error occurs that PostgREST can identify (like RLS, constraint violation),
        # it often raises an APIError. If the call is successful, response.data will contain the data.
        return response.data[0] if response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding enquiry")
    except Exception as e: # Catch any other unexpected errors
        return None, _format_error_message(e, "Unexpected error adding enquiry")


def get_enquiries():
    try:
        response = supabase.table("enquiries").select("*").order("created_at", desc=True).execute()
        return response.data, None
    except (APIError, HTTPStatusError) as e:
        return [], _format_error_message(e, "Error fetching enquiries")
    except Exception as e:
        return [], _format_error_message(e, "Unexpected error fetching enquiries")


def get_enquiry_by_id(enquiry_id: str):
    try:
        response = supabase.table("enquiries").select("*").eq("id", enquiry_id).single().execute()
        # .single() will raise an error if not exactly one row is found (or 0 if allow_empty=True was used, which it isn't here by default)
        # However, if 0 rows are found, it might raise a PostgrestAPIError with a specific code.
        # If more than 1 row, it will also error.
        return response.data, None
    except APIError as e:
        # Specifically handle cases where .single() finds 0 rows if that's the error type
        if "PGRST116" in str(e.message) or "Expected 1 row" in str(e.message): # PGRST116 is "Searched for a single row, but found 0"
            return None, None # Not found is not an application error in this context
        return None, _format_error_message(e, f"Error fetching enquiry {enquiry_id}")
    except HTTPStatusError as e:
        return None, _format_error_message(e, f"HTTP error fetching enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching enquiry {enquiry_id}")


def add_itinerary(enquiry_id: str, itinerary_text: str):
    try:
        response = supabase.table("itineraries").insert({
            "enquiry_id": enquiry_id,
            "itinerary_text": itinerary_text
        }).execute()
        return response.data[0] if response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding itinerary")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding itinerary")


def get_itinerary_by_enquiry_id(enquiry_id: str):
    try:
        # .maybe_single() is preferred if 0 or 1 row is expected, returns None if 0 rows.
        response = supabase.table("itineraries").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        return response.data, None # response.data will be None if not found
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
        return response.data[0] if response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding vendor reply")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding vendor reply")


def get_vendor_reply_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table("vendor_replies").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        return response.data, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching vendor reply for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching vendor reply for enquiry {enquiry_id}")


def add_quotation(enquiry_id: str, quotation_text: str, itinerary_id: str = None, vendor_reply_id: str = None):
    insert_data = {
        "enquiry_id": enquiry_id,
        "quotation_text": quotation_text
    }
    if itinerary_id:
        insert_data["itinerary_used_id"] = itinerary_id
    if vendor_reply_id:
        insert_data["vendor_reply_used_id"] = vendor_reply_id
    
    try:
        response = supabase.table("quotations").insert(insert_data).execute()
        return response.data[0] if response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding quotation")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding quotation")


def get_quotation_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table("quotations").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        return response.data, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching quotation for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching quotation for enquiry {enquiry_id}")