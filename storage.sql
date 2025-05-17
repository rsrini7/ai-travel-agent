-- In Supabase SQL Editor for the 'quotations' bucket policies:
-- To allow anonymous users to upload to a folder named 'public' or any top-level path
CREATE POLICY "Anon Uploads" ON storage.objects FOR INSERT TO anon WITH CHECK (bucket_id = 'quotations');
-- To allow anonymous users to read objects
CREATE POLICY "Anon Reads" ON storage.objects FOR SELECT TO anon USING (bucket_id = 'quotations');