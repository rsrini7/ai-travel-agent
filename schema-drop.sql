-- Drop all database objects in reverse order of creation to handle dependencies

-- First drop RLS policies
DROP POLICY IF EXISTS "Public anon access" ON public.quotations;
DROP POLICY IF EXISTS "Public anon access" ON public.vendor_replies;
DROP POLICY IF EXISTS "Public anon access" ON public.itineraries;
DROP POLICY IF EXISTS "Public anon access" ON public.enquiries;

-- Then drop indexes
DROP INDEX IF EXISTS public.idx_quotations_enquiry_id;
DROP INDEX IF EXISTS public.idx_vendor_replies_enquiry_id;
DROP INDEX IF EXISTS public.idx_itineraries_enquiry_id;

-- Finally drop tables in reverse order of creation
DROP TABLE IF EXISTS public.quotations;
DROP TABLE IF EXISTS public.vendor_replies;
DROP TABLE IF EXISTS public.itineraries;
DROP TABLE IF EXISTS public.enquiries;