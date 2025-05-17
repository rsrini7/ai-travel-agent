from pdf2docx import Converter
import io

def convert_pdf_bytes_to_docx_bytes(pdf_bytes):
    """
    Converts a PDF file (provided as bytes) to a docx file (also as bytes).

    Args:
        pdf_bytes (bytes): The bytes of the PDF file.

    Returns:
        bytes: The bytes of the docx file.
               Returns None if an error occurs during conversion.
    """
    try:
        cv = Converter(stream=pdf_bytes)
        docx_stream = io.BytesIO()
        cv.convert(docx_stream)
        cv.close()
        return docx_stream.getvalue()
    except Exception as e:
         print(f"An error occurred during conversion: {e}")
         return None