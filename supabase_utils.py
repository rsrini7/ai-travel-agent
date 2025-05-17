# supabase_utils.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from postgrest import APIError
from httpx import HTTPStatusError

load_dotenv()

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
        return response.data if response else [], None # Check if response itself is None
    except (APIError, HTTPStatusError) as e:
        return [], _format_error_message(e, "Error fetching enquiries")
    except Exception as e:
        return [], _format_error_message(e, "Unexpected error fetching enquiries")


def get_enquiry_by_id(enquiry_id: str):
    try:
        response = supabase.table("enquiries").select("*").eq("id", enquiry_id).single().execute()
        return response.data if response else None, None # Check if response itself is None
    except APIError as e:
        if "PGRST116" in str(e.message) or "Expected 1 row" in str(e.message):
            return None, None
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
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding itinerary")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding itinerary")

# --- MODIFIED GET FUNCTIONS BELOW ---
def get_itinerary_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table("itineraries").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        # If response is None, or if response.data is None (for maybe_single when not found), return None for data.
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching itinerary for enquiry {enquiry_id}")
    except Exception as e: # Catch AttributeError or other unexpected issues
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


def add_quotation(enquiry_id: str, quotation_text: str, itinerary_used_id: str = None, vendor_reply_used_id: str = None):
    insert_data = { "enquiry_id": enquiry_id, "quotation_text": quotation_text }
    if itinerary_used_id: 
        insert_data["itinerary_used_id"] = itinerary_used_id
    if vendor_reply_used_id: 
        insert_data["vendor_reply_used_id"] = vendor_reply_used_id
        
    try:
        response = supabase.table("quotations").insert(insert_data).execute()
        return response.data[0] if response and response.data else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, "Error adding quotation")
    except Exception as e:
        return None, _format_error_message(e, "Unexpected error adding quotation")


def get_quotation_by_enquiry_id(enquiry_id: str):
    try:
        response = supabase.table("quotations").select("*").eq("enquiry_id", enquiry_id).order("created_at", desc=True).limit(1).maybe_single().execute()
        return response.data if response else None, None
    except (APIError, HTTPStatusError) as e:
        return None, _format_error_message(e, f"Error fetching quotation for enquiry {enquiry_id}")
    except Exception as e:
        return None, _format_error_message(e, f"Unexpected error fetching quotation for enquiry {enquiry_id}")