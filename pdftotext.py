from fastapi import FastAPI, UploadFile, HTTPException
import pdfplumber
from tempfile import SpooledTemporaryFile
import google.generativeai as genai
from fpdf import FPDF
import logging
import os

app = FastAPI()

# Use your actual API key obtained from Google AI Studio
GOOGLE_API_KEY = "AIzaSyC9nJ3vsh0FBt6BPqi0N2ZTN2xM-Y9zkAo"
genai.configure(api_key=GOOGLE_API_KEY)

def process_pdf_file(file_content):
    try:
        with pdfplumber.open(file_content) as pdf:
            text_content = "".join(page.extract_text() for page in pdf.pages)
            return text_content
    except Exception as e:
        print(f"Error processing PDF: {e}")
        raise HTTPException(status_code=422, detail="Invalid PDF file")

def generate_text_response(prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text

def create_pdf(content, output_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(output_file)

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = UploadFile(...)):
    try:
        # ... (file validation and reading)

        with SpooledTemporaryFile(max_size=10 * 1024 * 1024, mode="wb") as temp_file:
            temp_file.write(await file.read())
            temp_file.seek(0)  # Explicitly rewind to start

            try:
                text_content = process_pdf_file(temp_file)
            except pdfplumber.PdfReadError as e:
                logging.error("Error processing PDF: %s", e)
                raise HTTPException(status_code=422, detail="Invalid PDF structure") from e

            try:
                gemini_response = generate_text_response(text_content)
            except google.generativeai.ApiRequestError as e:
                logging.error("Error calling Gemini API: %s", e)
                raise HTTPException(status_code=500, detail="Gemini API error") from e

            output_pdf_path = "output.pdf"  # Set your desired output path
            try:
                create_pdf(gemini_response, output_pdf_path)
            except fpdf.FPDFException as e:
                logging.error("Error creating PDF: %s", e)
                raise HTTPException(status_code=500, detail="PDF creation error") from e

        # Ensure temporary file cleanup
            temp_file.close()

        return {"file_content": text_content, "gemini_response": gemini_response, "output_pdf_path": output_pdf_path}

    except Exception as e:
        logging.exception("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error") from e