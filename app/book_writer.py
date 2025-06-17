# app/book_writer.py
from openai import OpenAI
import os

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4-1106-preview"

def generate_chapter(prompt: str, max_tokens=2048) -> str:
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.75,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()

def generate_full_book(prompt: str, chapters: list[str]) -> str:
    book = []

    book.append("## Prologue\n\n" + generate_chapter(f"Write a prologue for a Star Wars novel about: {prompt}", max_tokens=2000))

    for i, chapter_title in enumerate(chapters):
        chapter_prompt = f"Write Chapter {i+1} titled '{chapter_title}' in detail (1500+ words) for a Star Wars book about: {prompt}"
        text = generate_chapter(chapter_prompt, max_tokens=2000)
        book.append(f"\n\n## Chapter {i+1}: {chapter_title}\n\n{text}")

    book.append("\n\n## Epilogue\n\n" + generate_chapter(f"Write an epilogue for a Star Wars book about: {prompt}", max_tokens=2000))

    return "\n".join(book)

def generate_user_prompt_driven_book(prompt: str) -> str:
    long_chapter_titles = [f"Chapter {i+1}" for i in range(25)]  # 25 chapters
    return generate_full_book(prompt, long_chapter_titles)
