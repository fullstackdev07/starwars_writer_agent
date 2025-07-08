# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from app.book_writer import generate_user_prompt_driven_book, generate_book_title
from app.book_pdf_exporter import save_book_as_pdf
from dotenv import load_dotenv
import os
import re
import traceback

# Load environment variables from a .env file
load_dotenv()

app = FastAPI(
    title="Star Wars Book Generator",
    description="An API to generate a personalized Star Wars fan novel based on a user prompt.",
    version="4.0.0"
)

class BookRequest(BaseModel):
    user_input: str
    num_pages: int = 100  # Capped and defaulted to 100 as per client request

def sanitize_filename(text: str) -> str:
    """Sanitizes a string to be a valid filename."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", text)
    return sanitized[:50].strip().replace(' ', '_')

@app.post("/generate-book/", summary="Generate a Star Wars Book")
async def generate_star_wars_book(request: BookRequest):
    """
    Generates a full, multi-section Star Wars novel based on a user's prompt,
    with a fixed page cap, AI-generated image, and professional formatting.
    """
    user_prompt = request.user_input.strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    # Enforce the 100-page cap
    final_page_count = min(request.num_pages, 100)
    print(f"Processing request for a {final_page_count}-page book.")

    try:
        print("Generating a unique book title...")
        raw_title = await generate_book_title(user_prompt)
        book_title = raw_title.replace("#", "").strip()
        print(f"Generated Title: {book_title}")

        # --- Generate all book components (text, image, etc.) ---
        print(f"Generating book components for prompt: '{user_prompt}'...")
        book_data = await generate_user_prompt_driven_book(
            prompt=user_prompt,
            num_pages=final_page_count
        )
        print("Book components generated successfully.")

        # --- Generate and save the PDF with the new structure ---
        filename = f"{sanitize_filename(book_title)}.pdf"
        print(f"Generating PDF: {filename}...")
        
        # Pass the entire book_data dictionary to the PDF exporter
        output_pdf_path = await run_in_threadpool(
            save_book_as_pdf,
            title=book_title,
            book_data=book_data,
            filename=filename
        )
        print(f"PDF saved to: {output_pdf_path}")

        return {
            "title": book_title,
            "prompt": user_prompt,
            "pdf_file": output_pdf_path,
            "preview": book_data.get('prologue_text', '')[:1500] + "..."
        }
    except Exception as e:
        print(f"An error occurred during book generation: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")