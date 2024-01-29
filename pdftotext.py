from fpdf import FPDF
import google.generativeai as genai
from fastapi import FastAPI, __version__,UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import logging
import os
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key="AIzaSyBbeOPkTwH3FuubFZxN5ZgSkpmafzuXN0k")

generation_config = {
    "temperature": 0.8,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

prompt_parts = ["Just write one work for the given doc -- DOC STARTS --"]

def process_pdf_file(file_content):
    try:
        with pdfplumber.open(file_content) as pdf:
            text_content = "".join(page.extract_text() for page in pdf.pages)
            return text_content
    except Exception as e:
        print(f"Error processing PDF: {e}")
        raise HTTPException(status_code=422, detail=b"Invalid PDF file")

def generate_summary(prompt):
    model = genai.GenerativeModel(
        model_name="gemini-pro",
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    response = model.generate_content(prompt)
    print(response.text)
    return response.text

def generate_text_response(prompt, max_tokens_per_request=8000):
    model = genai.GenerativeModel(
        model_name="gemini-pro",
        generation_config=generation_config,
        safety_settings=safety_settings,
    )

    text_parts = [prompt[-1][i:i + max_tokens_per_request] for i in range(0, len(prompt[-1]), max_tokens_per_request)]

    response_parts = []
    for part in text_parts:
        print(part)
        part_prompt = prompt.copy()
        part_prompt[-1] = part

        try:
            response_part = model.generate_content(part_prompt)
            response_parts.append(response_part.text)
        except UnicodeEncodeError as e:
            logging.error("Error calling Gemini API: %s", e)
            raise HTTPException(status_code=500, detail="Gemini API error") from e

    combined_response = "\n".join(response_parts)
    return combined_response


def create_pdf(content, output_file):
    if content is not None and isinstance(content, str):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        try:
            content = content.encode("latin-1", "replace").decode("latin-1")
        except UnicodeEncodeError as e:
            logging.error(f"Error encoding content: {e}")
            raise HTTPException(
                status_code=500, detail="Content encoding error"
            ) from e

        pdf.multi_cell(0, 10, content)

        try:
            if os.path.exists(output_file):
                existing_pdf = FPDF()
                existing_pdf.add_page()
                existing_pdf.set_auto_page_break(auto=True, margin=15)
                existing_pdf.set_font("Arial", size=12)

                existing_pdf.output(output_file, "F")
                with open(output_file, "rb") as file:
                    existing_content = file.read()

                content = existing_content + content.encode("latin-1", "replace")

            pdf.output(output_file, "F")
        except Exception as e:
            logging.error(f"Error creating PDF: {e}")
            raise HTTPException(status_code=500, detail="PDF creation error") from e
    else:
        logging.error(f"Invalid content provided for PDF: {content}")
        raise HTTPException(status_code=500, detail="Invalid content for PDF")

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    try:
        temp_file = io.BytesIO(await file.read())

        try:
            text_content = process_pdf_file(temp_file)
            # print("----------------------------------------------------------------------------------- The res is "+text_content +"---------------------------------------------------------------------------------------")
        except Exception as e:
            logging.error("Error processing PDF: %s", e)
            raise HTTPException(status_code=422, detail="Invalid PDF structure") from e

        prompt_parts[-1] = (
        #    "Perform abstractive summarization of 1500 words in paragraph for the given document read it and understand then generate. Craft the summary in plain, easy-to-understand language, avoiding any legal or complex terms. Pay special attention to providing a clear understanding of the policy's key details. Elaborate on each aspect in a manner accessible to individuals with diverse educational backgrounds, prioritizing simplicity and clarity. Aim to create a comprehensive summary that empowers individuals with knowledge, reducing the risk of potential scams. Ensure that the generated output matches the length specified, and include all relevant contact details at the end for further inquiries or clarifications "
        "Generate an abstractive summarization and simplified 2500-word paragraph summary for the given document. Understand the text and Craft the summary in plain, easy-to-understand language, avoiding any legal or complex terms. Pay special attention to providing a clear understanding of the policy's key details, including coverage, exclusions, and vital considerations for the policyholder. Elaborate on each aspect in a manner accessible to individuals with diverse educational backgrounds, prioritizing simplicity and clarity. Aim to create a comprehensive summary that empowers individuals with knowledge, reducing the risk of potential scams. Ensure that the generated output matches the length specified, and include all relevant contact details at the end for further inquiries or clarifications from the details Provied"
        + text_content
        )

        try:
            gemini_response_summary = generate_summary(prompt_parts)
            print( prompt_parts)
            print("----------------------------------------------------------------------------------- The res is " + gemini_response_summary + "---------------------------------------------------------------------------------------")
        except UnicodeEncodeError as e:
            logging.error("Error calling Gemini API: %s", e)
            raise HTTPException(status_code=500, detail="Gemini API error") from e

        simplified_prompt_parts = [
            "Just write one work for the given doc -- DOC STARTS --",
        ]

        simplified_prompt_parts[-1] = (
            "Perform abstractive summarization on the given legal document. The goal is to create a summary that is close in length to the original document. Prioritize clarity and simplicity by converting complex and legal terms into easily understandable language. Aim for an output length that is as close as possible to the input, maintaining coherence and relevance.Eliminate unnecessary complexity to make the summary accessible to individuals with diverse educational backgrounds."
            + text_content
        )

        try:
            gemini_response_simplified = generate_text_response(
                simplified_prompt_parts
            )
        except UnicodeEncodeError as e:
            logging.error("Error calling Gemini API: %s", e)
            raise HTTPException(status_code=500, detail="Gemini API error") from e

        combined_response = (
            gemini_response_summary + "\n\n---------------------------\n\nSimplified DOC\n\n ---------------------------" + gemini_response_simplified
        )

        output_pdf_path = "output.pdf"
        try:
            create_pdf(combined_response, output_pdf_path)
        except Exception as e:
            logging.error("Error creating PDF: %s", e)
            raise HTTPException(status_code=500, detail="PDF creation error") from e

        return FileResponse(
            output_pdf_path, filename="output.pdf", media_type="application/pdf"
        )

    except Exception as e:
        logging.exception("Unexpected error: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal Server Error"
        ) from e


html = f"""
<!DOCTYPE html>
<html>
    <head>
        <title>FastAPI on Vercel</title>
        <link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
    </head>
    <body>
        <div class="bg-gray-200 p-4 rounded-lg shadow-lg">
            <h1>Hello from </h1>
            <ul>
                <li><a href="/docs">/docs</a></li>
                <li><a href="/redoc">/redoc</a></li>
            </ul>
            <p>Powered by <a href="https://vercel.com" target="_blank">Vercel</a></p>
        </div>
    </body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(html)