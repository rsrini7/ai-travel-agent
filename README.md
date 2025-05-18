# AI-Powered Travel Agent Automation
Welcome to the AI-Powered Travel Agent Automation project! This project is a Streamlit application designed to automate the process of travel agent tasks, including managing travel enquiries, generating itinerary suggestions, inputting vendor replies, and generating professional-looking quotations in PDF and DOCX formats. The system leverages Large Language Models (LLMs) for content generation and Supabase for backend data storage and file management.

---

## 🚀 Overview

This project is a **AI Travel Agent** demonstrating an AI-powered travel automation system. It allows users to manage travel enquiries, generate itinerary suggestions, input vendor replies, and automatically create professional-looking quotations in PDF and DOCX formats. The system leverages Large Language Models (LLMs) for content generation and Supabase for backend data storage and file management.

---

## ✨ Features

- **Enquiry Management:**
  - Submit new travel enquiries with details like destination, duration, number of travelers, trip type, and client information.
- **AI Itinerary Suggestions:**
  - Generate AI-powered suggestions for places and attractions based on enquiry details.
  - Selectable AI providers (Google Gemini, OpenRouter, Groq).
- **Vendor Reply Integration:**
  - Input and store vendor replies, including pricing, inclusions, and exclusions.
- **AI Quotation Generation:**
  - Automatically generate structured quotation data using LLMs based on enquiry, itinerary, and vendor reply.
  - Produce downloadable PDF quotations with a professional layout.
  - Convert generated PDFs to DOCX format.
- **Cloud Storage:**
  - Store generated quotation documents (PDF, DOCX) in Supabase Storage.
- **Data Persistence:**
  - All enquiries, client details, itineraries, vendor replies, and quotation metadata are stored in a Supabase PostgreSQL database.
- **Configurable AI:**
  - Choose between different AI providers (Gemini, OpenRouter, Groq) for content generation tasks.
  - Specify default models for OpenRouter and Groq via environment variables.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Backend & Database:** Supabase (PostgreSQL, Storage)
- **AI/LLM Integration:**
  - Langchain
  - LangGraph (for orchestrating quotation generation steps)
  - LLM Providers: Google Gemini, OpenRouter, Groq
- **Document Generation:**
  - FPDF2 (`fpdf`) for PDF creation
  - `pdf2docx` for PDF to DOCX conversion
- **Environment Management:** `python-dotenv`
- **Programming Language:** Python 3.11

---

## 📁 Project Structure

```text
.
├── app.py                          # Main Streamlit application
├── sidebar.py                      # Global sidebar configuration and UI
├── llm_prompts.py                  # LLM prompt templates and configurations
├── llm_providers.py                # LLM provider integration (Gemini, OpenRouter)
├── pdf_utils.py                    # PDF generation logic using FPDF2
├── docx_utils.py                   # PDF to DOCX conversion utility
├── supabase_utils.py               # Supabase database and storage utilities
├── itinerary_generator.py          # AI-powered itinerary generation logic
├── quotation_graph_builder.py      # LangGraph workflow for quotation generation
├── tab1_new_enquiry.py             # Streamlit tab for new travel enquiries
├── tab2_manage_itinerary.py        # Streamlit tab for managing itineraries
├── tab3_vendor_quotation.py        # Streamlit tab for vendor quotations
├── schema.sql                      # Supabase database schema (tables)
├── schema-drop.sql                 # Script to drop database tables (for dev/reset)
├── storage.sql                     # Supabase Storage bucket policies
├── requirements.txt                # Python dependencies
├── .python-version                 # Specifies Python version (3.11)
├── .env.example                    # Environment variable template
├── assets/                         # Static assets for PDF generation
│   ├── fonts/
│   │   ├── DejaVuSansCondensed.ttf
│   │   ├── DejaVuSansCondensed-Bold.ttf
│   │   └── DejaVuSansCondensed-Oblique.ttf
│   ├── top_banner.png              # (User needs to provide)
│   └── tripexplore-logo-with-rating.png # (User needs to provide)
└── README.md                       # This file
```

---

## ⚙️ Setup and Installation

### Prerequisites

- Python 3.11
- A Supabase account (for database and storage)
- API Keys:
  - Google API Key (if using Gemini)
  - OpenRouter API Key (if using OpenRouter)

### Steps

1. **Clone the Repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```
2. **Create a Virtual Environment and Activate it:**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up Environment Variables:**
   - Copy `.env.example` to a new file named `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and fill in your actual credentials:
     ```env
     SUPABASE_URL="YOUR_SUPABASE_URL"
     SUPABASE_KEY="YOUR_SUPABASE_ANON_KEY" # Or service_role key if needed for specific policies
     GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
     OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY"
     OPENROUTER_DEFAULT_MODEL="google/gemini-flash-1.5" # Example, can be overridden
     OPENROUTER_HTTP_REFERER="http://localhost:3000" # Optional, set your app's URL
     OPENROUTER_APP_TITLE="AI Travel Quotation" # Optional, set your app's title
     GROQ_API_KEY="YOUR_GROQ_API_KEY"
     GROQ_DEFAULT_MODEL="llama3-8b-8192" # Optional, specify default Groq model
     ```
5. **Supabase Setup:**
   - Go to your Supabase project dashboard.
   - **Database:**
     - Navigate to the "SQL Editor".
     - Click "+ New query" and run the contents of `schema.sql` to create the necessary tables.
     - (For development/reset, you can use `schema-drop.sql` to remove tables.)
   - **Storage:**
     - Navigate to "Storage".
     - Click "Create a new bucket".
     - Name the bucket `quotations`. Make it a public bucket if you want direct public URLs, or keep it private and rely on signed URLs (the app handles both).
     - Go back to the "SQL Editor" and run the contents of `storage.sql` to set up access policies for the `quotations` bucket. This allows anonymous uploads and reads as configured in the file.
6. **Prepare Assets (for PDF Generation):**
   - The PDF generation uses custom fonts and images.
   - The DejaVu fonts are included in `assets/fonts/`.
   - You need to provide the following image files in the `assets/` directory:
     - `assets/top_banner.png` (a banner image for the top of the PDF)
     - `assets/tripexplore-logo-with-rating.png` (a logo image)
   - If these images are not present, the PDF generation will print warnings and skip them.

---

## ▶️ Running the Application

Once the setup is complete, run the Streamlit application:

```bash
streamlit run app.py
```

The application will open in your web browser, typically at [http://localhost:8501](http://localhost:8501).

---

## 📖 Usage

The application is organized into three main tabs:

1. **📝 New Enquiry:**
   - Fill in the travel details (Destination, Number of Days, Travelers, Trip Type).
   - Provide client information (Name, Mobile, City, Email).
   - Click "Submit Enquiry" to save the information to Supabase.
2. **🔍 Manage Enquiries & Itinerary:**
   - Select an existing enquiry from the dropdown list.
   - View the details of the selected enquiry.
   - If an AI-generated itinerary already exists, it will be displayed.
   - Click "Generate Places Suggestions" to use an LLM (selected via the sidebar AI Configuration) to suggest places/attractions for the trip. The suggestions will be saved.
3. **✍️ Add Vendor Reply & Generate Quotation:**
   - Select an enquiry. Its details and any existing itinerary/vendor reply will be loaded.
   - **Add/View Vendor Reply:**
     - Input or update the vendor's reply, including details like pricing, inclusions, exclusions, hotel information, etc.
     - Click "Submit/Update Vendor Reply" to save it.
   - **AI Quotation Generation:**
     - Ensure a vendor reply is available.
     - The system uses the enquiry details, AI-generated itinerary (from Tab 2 or database), and the vendor reply to generate a quotation.
     - Click "Generate Quotation PDF" to:
       1. Use an LLM to structure all information into a JSON.
       2. Generate a PDF document from this JSON.
       3. Upload the PDF to Supabase Storage.
       4. Save the quotation metadata (including the JSON and storage path) to the database.
     - Click "Generate Quotation DOCX" to:
       1. Perform the same LLM structuring and PDF generation as above.
       2. Convert the generated PDF bytes into DOCX format.
       3. Upload the DOCX to Supabase Storage.
       4. Update the quotation record in the database with the DOCX storage path.
   - **Download/View Quotation Files:**
     - Links to download/view stored PDF and DOCX files from Supabase Storage will appear (public or signed URLs).
     - Buttons to download locally generated PDF/DOCX files (from the current session before potential re-runs or selection changes) will also be available.

### Global AI Configuration (Sidebar)

- Use the sidebar to select the AI Provider (Gemini or OpenRouter) that will be used for all LLM tasks (itinerary suggestions, quotation structuring).
- The currently active provider and model (for OpenRouter) are displayed.

---

## 🔑 Environment Variables

The application requires the following environment variables to be set in the `.env` file:

- `SUPABASE_URL`: Your Supabase project URL.
- `SUPABASE_KEY`: Your Supabase anon key (or service role key if your RLS policies require it).
- `GOOGLE_API_KEY`: Your API key for Google AI Studio (for Gemini).
- `GROQ_API_KEY`: Your API key for Groq (for Groq models).
- `GROQ_DEFAULT_MODEL`: (Optional) Default model to use with Groq (default: 'llama3-8b-8192').
- `OPENROUTER_API_KEY`: Your API key for OpenRouter.ai.
- `OPENROUTER_DEFAULT_MODEL`: (Optional) The default model to use with OpenRouter (e.g., `google/gemini-flash-1.5`, `openai/gpt-3.5-turbo`). Defaults to `google/gemini-flash-1.5` if not set.
- `OPENROUTER_HTTP_REFERER`: (Optional) Your site URL or app name, sent as `HTTP-Referer` to OpenRouter. Defaults to `http://localhost:3000`.
- `OPENROUTER_APP_TITLE`: (Optional) Your app's title, sent as `X-Title` to OpenRouter. Defaults to `AI Travel Quotation`.

---

## 📊 Supabase Schema

The application uses the following tables in Supabase:

- `enquiries`: Stores initial customer travel enquiries.
- `clients`: Stores client/customer information linked to enquiries.
- `itineraries`: Stores AI-generated itineraries/place suggestions for enquiries.
- `vendor_replies`: Stores vendor replies (pricing, terms) related to an enquiry.
- `quotations`: Stores final generated quotations, including the structured JSON data, links to PDF/DOCX files in Supabase Storage, and references to the itinerary/vendor reply versions used.

Refer to `schema.sql` for detailed table definitions and relationships.

---

## 💡 Future Development Ideas

- More sophisticated AI prompting for itineraries and quotations.
- User authentication and roles.
- Direct email integration for sending quotations.
- Advanced quotation template customization.
- Status tracking for enquiries (e.g., 'New', 'Itinerary Generated', 'Quotation Sent').
- Image integration within the PDF itinerary (e.g., destination photos).

---

## 📄 License

This project is licensed under the MIT License. (Note: A `LICENSE.md` file is not included in the provided project files, but MIT is a common choice for such projects.)