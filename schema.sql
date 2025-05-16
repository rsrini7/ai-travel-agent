CREATE TABLE public.enquiries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    destination TEXT NOT NULL,
    num_days INTEGER CHECK (num_days > 0),
    traveler_count INTEGER CHECK (traveler_count > 0),
    trip_type TEXT,
    status TEXT DEFAULT 'New' NOT NULL -- e.g., 'New', 'Itinerary Generated', 'Quotation Sent', 'Closed'
);

-- Optional: Add comments for clarity in Supabase UI
COMMENT ON TABLE public.enquiries IS 'Stores initial customer travel enquiries.';
COMMENT ON COLUMN public.enquiries.status IS 'Current status of the enquiry process.';

CREATE TABLE public.itineraries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enquiry_id UUID NOT NULL REFERENCES public.enquiries(id) ON DELETE CASCADE, -- Link to the enquiry
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    itinerary_text TEXT NOT NULL -- The full text of the generated itinerary
);

-- Optional: Index on enquiry_id for faster lookups
CREATE INDEX idx_itineraries_enquiry_id ON public.itineraries(enquiry_id);

COMMENT ON TABLE public.itineraries IS 'Stores AI-generated itineraries for enquiries.';
COMMENT ON COLUMN public.itineraries.enquiry_id IS 'Foreign key linking to the parent enquiry.';

CREATE TABLE public.vendor_replies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enquiry_id UUID NOT NULL REFERENCES public.enquiries(id) ON DELETE CASCADE, -- Link to the enquiry
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    reply_text TEXT NOT NULL -- The raw text of the vendor's reply
);

-- Optional: Index on enquiry_id for faster lookups
CREATE INDEX idx_vendor_replies_enquiry_id ON public.vendor_replies(enquiry_id);

COMMENT ON TABLE public.vendor_replies IS 'Stores vendor replies related to an enquiry.';
COMMENT ON COLUMN public.vendor_replies.enquiry_id IS 'Foreign key linking to the parent enquiry.';

CREATE TABLE public.quotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enquiry_id UUID NOT NULL REFERENCES public.enquiries(id) ON DELETE CASCADE, -- Link to the enquiry
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    quotation_text TEXT NOT NULL, -- The full text of the generated quotation
    itinerary_used_id UUID REFERENCES public.itineraries(id) ON DELETE SET NULL, -- Optional: which itinerary was used
    vendor_reply_used_id UUID REFERENCES public.vendor_replies(id) ON DELETE SET NULL -- Optional: which vendor reply was used
);

-- Optional: Index on enquiry_id for faster lookups
CREATE INDEX idx_quotations_enquiry_id ON public.quotations(enquiry_id);

COMMENT ON TABLE public.quotations IS 'Stores final generated quotations for clients.';
COMMENT ON COLUMN public.quotations.enquiry_id IS 'Foreign key linking to the parent enquiry.';
COMMENT ON COLUMN public.quotations.itinerary_used_id IS 'Foreign key to the specific itinerary version used for this quote.';
COMMENT ON COLUMN public.quotations.vendor_reply_used_id IS 'Foreign key to the specific vendor reply version used for this quote.';

-- Enable RLS and create policies for all tables
ALTER TABLE public.itineraries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public anon access"
ON public.itineraries
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

ALTER TABLE public.vendor_replies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public anon access"
ON public.vendor_replies
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

ALTER TABLE public.quotations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public anon access"
ON public.quotations
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

ALTER TABLE public.enquiries ENABLE ROW LEVEL SECURITY; 
CREATE POLICY "Public anon access"
ON public.enquiries
FOR ALL
TO anon
USING (true)
WITH CHECK (true);
