# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.book_writer import generate_user_prompt_driven_book
from app.book_pdf_exporter import save_book_as_pdf
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

class BookRequest(BaseModel):
    user_input: str
    num_pages: int = 100  # default to 100 pages if not provided

@app.post("/generate-book/")
async def generate_star_wars_book(data: BookRequest):
    prompt = data.user_input.strip()
    num_pages = data.num_pages

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    # Generate long-form book (~200 pages)
    book_text = generate_user_prompt_driven_book(user_prompt)

    # Generate and save PDF
    filename = f"{user_prompt[:30].replace(' ', '_')}.pdf"
    output_pdf_path = save_book_as_pdf("Your Star Wars Story", book_text, filename=filename)

    return {
        "title": "Your Star Wars Story",
        "prompt": user_prompt,
        "pdf_file": output_pdf_path,
        "preview": book_text[:1200] + "..."  # Optional
    }