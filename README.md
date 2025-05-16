```markdown
# AI-Powered End-to-End Travel Automation System (MVP)

This project is a Minimum Viable Product (MVP) for an AI-powered system designed to automate various aspects of travel business operations, focusing on enquiry intake, itinerary research, and quotation generation.

**Live Demo:** [Link to your Streamlit Cloud deployment if you have one]
**GitHub Repository:** [https://github.com/rsrini7/ai-travel-agent](https://github.com/rsrini7/ai-travel-agent)

## Overview

The system aims to streamline the process for travel agents by:
1.  Accepting customer travel enquiries.
2.  Utilizing AI (Large Language Models) to research and generate draft itineraries.
3.  Processing vendor replies (e.g., pricing, inclusions).
4.  Generating formatted quotations for customers by combining itinerary and vendor information with AI assistance.

This MVP demonstrates the core workflow using Python, Streamlit for the UI, Langchain & LangGraph for AI orchestration, and Supabase as the backend database.

## Features (MVP)

*   **Enquiry Intake:**
    *   Web form to capture customer travel details (destination, dates, travelers, trip type).
    *   Enquiries are stored in a Supabase database.
*   **AI Itinerary Generation:**
    *   Generate a day-wise itinerary based on enquiry details using a Large Language Model (currently configured for Google Gemini 1.5 Flash).
    *   Generated itineraries are stored and linked to the original enquiry.
*   **Vendor Reply Intake:**
    *   Interface to input plain text vendor replies (containing pricing, inclusions/exclusions).
    *   Vendor replies are stored and linked to the relevant enquiry.
*   **AI-Powered Quotation Generation:**
    *   Combines the AI-generated itinerary and parsed vendor reply information using LangGraph and an LLM.
    *   Outputs a structured quotation draft.
    *   Quotations are stored and linked to the enquiry.
*   **Basic Management UI:**
    *   View lists of enquiries.
    *   Select an enquiry to view its details, generated itinerary, vendor reply, and quotation.
    *   Trigger generation steps for selected enquiries.

## Technology Stack

*   **Backend:** Python
*   **Frontend/UI:** Streamlit
*   **AI Orchestration:** Langchain, LangGraph
*   **Large Language Model (LLM):** Google Gemini 1.5 Flash (configurable)
*   **Database:** Supabase (PostgreSQL)
*   **Environment Management:** `python-dotenv`

## Project Structure

```
ai-travel-agent/
├── app.py                   # Main Streamlit application
├── supabase_utils.py        # Functions for Supabase interaction
├── llm_utils.py             # Functions for Langchain/LangGraph LLM interactions
├── requirements.txt         # Python dependencies
├── .env.example             # Example for environment variables
└── README.md                # This file
```

## Setup and Installation

### Prerequisites

*   Python 3.10+
*   Supabase Account: [https://supabase.com/](https://supabase.com/)
*   Google Cloud Project with Generative Language API (Gemini API) enabled.
    *   Obtain a Google API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) or your Google Cloud Console.

### 1. Clone the Repository

```bash
git clone https://github.com/rsrini7/ai-travel-agent.git
cd ai-travel-agent
```

### 2. Set up Supabase

1.  Create a new project in Supabase.
2.  **Enable `uuid-ossp` Extension:**
    *   In your Supabase project dashboard, go to `Database` -> `Extensions`.
    *   Search for `uuid-ossp` and enable it.
3.  **Create Tables:**
    *   Go to `SQL Editor` in your Supabase dashboard.
    *   Run the SQL commands provided in the [Database Schema](#database-schema) section below (or use the SQL provided earlier in project discussions if available separately).
4.  **Configure Row Level Security (RLS):**
    *   For MVP/development, you can temporarily disable RLS for the created tables or create permissive policies.
    *   Example (run in SQL Editor for each table, e.g., `public.enquiries`):
        ```sql
        ALTER TABLE public.enquiries ENABLE ROW LEVEL SECURITY;
        CREATE POLICY "Public anon access"
        ON public.enquiries
        FOR ALL
        TO anon
        USING (true)
        WITH CHECK (true);
        ```
        Repeat for `itineraries`, `vendor_replies`, and `quotations` tables.
        **Caution:** For production, implement stricter RLS policies.

### 3. Set up Environment Variables

1.  Create a `.env` file in the root of the project directory:
    ```bash
    cp .env.example .env
    ```
2.  Edit the `.env` file with your credentials:
    ```
    SUPABASE_URL="YOUR_SUPABASE_URL"
    SUPABASE_KEY="YOUR_SUPABASE_ANON_KEY" # Or your service_role key if needed for specific policies
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    ```
    *   Find `SUPABASE_URL` and `SUPABASE_KEY` (anon key) in your Supabase project settings under `API`.

### 4. Create a Virtual Environment and Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run the Application

```bash
streamlit run app.py
```
The application should open in your web browser, typically at `http://localhost:8501`.

## Usage Flow

1.  **Submit New Enquiry:** Go to the "📝 New Enquiry" tab and fill in the travel details.
2.  **Manage Enquiries & Generate:**
    *   Go to the "🔍 Manage Enquiries & Generate" tab.
    *   Select the newly created (or an existing) enquiry from the dropdown.
    *   Click "Generate Itinerary with AI". View the generated itinerary.
3.  **Add Vendor Reply:**
    *   Go to the "✍️ Add Vendor Reply" tab.
    *   Select the same enquiry.
    *   Input the vendor's reply text (including pricing, inclusions, etc.).
4.  **Generate Quotation:**
    *   Return to the "🔍 Manage Enquiries & Generate" tab.
    *   Ensure the correct enquiry is selected.
    *   Click "Generate Quotation with AI". View the generated quotation.

## Database Schema

The following tables are used in Supabase:

*   **`enquiries`**: Stores initial customer travel enquiries.
    *   `id` (UUID, PK)
    *   `created_at` (TIMESTAMPTZ)
    *   `destination` (TEXT)
    *   `num_days` (INTEGER)
    *   `traveler_count` (INTEGER)
    *   `trip_type` (TEXT)
    *   `status` (TEXT, e.g., 'New', 'Itinerary Generated')
*   **`itineraries`**: Stores AI-generated itineraries.
    *   `id` (UUID, PK)
    *   `enquiry_id` (UUID, FK to `enquiries.id`)
    *   `created_at` (TIMESTAMPTZ)
    *   `itinerary_text` (TEXT)
*   **`vendor_replies`**: Stores vendor replies.
    *   `id` (UUID, PK)
    *   `enquiry_id` (UUID, FK to `enquiries.id`)
    *   `created_at` (TIMESTAMPTZ)
    *   `reply_text` (TEXT)
*   **`quotations`**: Stores generated quotations.
    *   `id` (UUID, PK)
    *   `enquiry_id` (UUID, FK to `enquiries.id`)
    *   `created_at` (TIMESTAMPTZ)
    *   `quotation_text` (TEXT)
    *   `itinerary_used_id` (UUID, FK to `itineraries.id`, nullable)
    *   `vendor_reply_used_id` (UUID, FK to `vendor_replies.id`, nullable)

*(For detailed `CREATE TABLE` statements, please refer to previous project discussions or inspect `supabase_utils.py` for schema comments if not explicitly listed here).*

## Future Enhancements (Beyond MVP)

*   **Advanced AI Learning:** Train models on past sample quotations for company-specific formatting and style.
*   **Email Integration:**
    *   Auto-filler for template-based vendor request emails.
    *   API-based email sender (SendGrid, Gmail API).
    *   Email inbox viewer for quotation replies from vendors.
*   **Sophisticated UI/UX:** More interactive elements, enquiry status tracking, editing capabilities.
*   **Enhanced Vendor Reply Parsing:** More robust extraction of structured data from vendor replies.
*   **User Authentication:** Secure access with user accounts.
*   **File Uploads:** For raw `.txt` files or other document types.
*   **Error Handling & Logging:** More comprehensive error management and logging.
*   **Testing:** Unit and integration tests.
*   **Deployment:** Streamlined deployment to cloud platforms (e.g., Streamlit Cloud, AWS, Google Cloud).

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

Please ensure your code follows existing style and includes relevant updates to documentation.

## License

This project is open-source and available under the [MIT License](LICENSE.txt) (You would need to create a LICENSE.txt file with the MIT license text).

---

*This `README.md` was generated based on project discussions and aims to provide a comprehensive starting point. Please update it as the project evolves.*
```

**Next Steps for You:**

1.  **Create `LICENSE.txt`:** If you choose the MIT license (common for open-source), create a file named `LICENSE.txt` in your project root and paste the MIT License text into it. You can easily find the MIT License text online.
2.  **Review and Customize:** Read through the generated `README.md`.
    *   Fill in the `[Link to your Streamlit Cloud deployment if you have one]` if applicable.
    *   Ensure the "Database Schema" section is accurate or clearly refers to where the SQL can be found. If you have the SQL `CREATE TABLE` statements handy from our previous discussion, you could paste them directly into a collapsible section within the README.
    *   Adjust any details that might have changed or that you want to emphasize.
3.  **Commit and Push:**
    ```bash
    git add README.md requirements.txt app.py supabase_utils.py llm_utils.py .env.example .gitignore # Add other files as needed
    git commit -m "feat: Initial project structure and README for AI Travel Agent MVP"
    git push origin main # or your default branch
    ```

This README should give visitors to your GitHub repository a good understanding of your project!