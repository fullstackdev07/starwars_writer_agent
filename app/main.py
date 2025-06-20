# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from app.book_writer import generate_user_prompt_driven_book, generate_book_title
from app.book_pdf_exporter import save_book_as_pdf
from dotenv import load_dotenv
import os
import re

# Load environment variables from a .env file
load_dotenv()

app = FastAPI(
    title="Star Wars Book Generator",
    description="An API to generate a personalized Star Wars fan novel based on a user prompt.",
    version="2.0.0"
)

class BookRequest(BaseModel):
    user_input: str
    num_pages: int = 20
    writing_sample: str | None = None

def sanitize_filename(text: str) -> str:
    """Sanitizes a string to be a valid filename."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", text)
    return sanitized[:50].strip().replace(' ', '_')

@app.post("/generate-book/", summary="Generate a Star Wars Book")
async def generate_star_wars_book(request: BookRequest):
    """
    Generates a full, multi-chapter Star Wars novel based on a user's prompt.
    """
    user_prompt = request.user_input.strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    try:
        # --- NEW: Clean the title after receiving it from the AI ---
        print("Generating a unique book title...")
        raw_title = await generate_book_title(user_prompt)
        # Clean the title to remove any unwanted characters like '#'
        book_title = raw_title.replace("#", "").strip()
        print(f"Generated and Cleaned Title: {book_title}")

        # --- Generate the full book text ---
        print(f"Generating book for prompt: '{user_prompt}'...")
        book_text = await generate_user_prompt_driven_book(
            prompt=user_prompt,
            num_pages=request.num_pages,
            writing_sample=request.writing_sample or ""
        )
        print("Book text generated successfully.")

        # --- Generate and save the PDF with the clean title ---
        filename = f"{sanitize_filename(book_title)}.pdf"
        print(f"Generating PDF: {filename}...")
        
        output_pdf_path = await run_in_threadpool(
            save_book_as_pdf,
            title=book_title,
            book_text=book_text,
            filename=filename
        )
        print(f"PDF saved to: {output_pdf_path}")

        return {
            "title": book_title,
            "prompt": user_prompt,
            "pdf_file": output_pdf_path,
            "preview": book_text[:1500] + "..."
        }
    except Exception as e:
        print(f"An error occurred during book generation: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")