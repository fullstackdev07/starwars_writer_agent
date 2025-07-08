# app/book_writer.py
from openai import AsyncOpenAI
import os
import asyncio
import re
import json
import random
import string
import httpx
from app.prompt_builder import (
    build_chapter_section_prompt, build_summarization_prompt,
    build_title_generation_prompt, build_data_selection_prompt,
    build_image_generation_prompt
)
from dotenv import load_dotenv

load_dotenv()

openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_TEXT = "gpt-4-1106-preview"
MODEL_IMAGE = "dall-e-3"

WORDS_PER_SECTION_TARGET = 750
MAX_TOKENS_PER_SECTION = 1200

# --- Data Loading ---
def load_all_swapi_data():
    data = {}
    data_dir = "swapi_data"
    if not os.path.exists(data_dir):
        raise FileNotFoundError("The 'swapi_data' directory was not found. Please run the fetch_swapi_data.py script first.")
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            category = filename.replace(".json", "")
            with open(os.path.join(data_dir, filename), "r", encoding='utf-8') as f:
                data[category] = json.load(f)
    return data

ALL_SWAPI_DATA = load_all_swapi_data()
print("SWAPI data loaded successfully.")

# --- Helper Functions ---
async def select_book_data_context(prompt: str) -> dict:
    selection_prompt = build_data_selection_prompt(prompt, ALL_SWAPI_DATA)
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": selection_prompt}],
        temperature=0.3, response_format={"type": "json_object"}
    )
    try:
        selected_names = json.loads(response.choices[0].message.content)
        print(f"AI selected data context: {selected_names}")
        book_context = {}
        for category, names in selected_names.items():
            if category in ALL_SWAPI_DATA:
                book_context[category] = [item for item in ALL_SWAPI_DATA[category] if item.get('name') in names or item.get('title') in names]
        return book_context
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing AI data selection, falling back to random. Error: {e}")
        return {
            "people": random.sample(ALL_SWAPI_DATA.get("people", []), min(len(ALL_SWAPI_DATA.get("people", [])), 5)),
            "planets": random.sample(ALL_SWAPI_DATA.get("planets", []), min(len(ALL_SWAPI_DATA.get("planets", [])), 3)),
            "starships": random.sample(ALL_SWAPI_DATA.get("starships", []), min(len(ALL_SWAPI_DATA.get("starships", [])), 2)),
        }

async def generate_book_image(prompt: str, data_context: dict) -> str:
    print("--- Generating AI book image ---")
    image_prompt = build_image_generation_prompt(prompt, data_context)
    print(f"DALL-E Prompt: {image_prompt}")
    try:
        response = await openai.images.generate(model=MODEL_IMAGE, prompt=image_prompt, size="1024x1024", quality="standard", n=1)
        image_url = response.data[0].url
        output_dir = "generated_images"
        os.makedirs(output_dir, exist_ok=True)
        image_filename = f"{''.join(random.choices(string.ascii_letters + string.digits, k=12))}.png"
        output_path = os.path.join(output_dir, image_filename)
        async with httpx.AsyncClient() as client:
            image_response = await client.get(image_url)
            image_response.raise_for_status()
            with open(output_path, "wb") as f: f.write(image_response.content)
        print(f"Image saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Could not generate image: {e}")
        return None

async def generate_book_title(prompt: str) -> str:
    title_prompt = build_title_generation_prompt(prompt, "book")
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": title_prompt}],
        temperature=0.8, max_tokens=20
    )
    return response.choices[0].message.content.strip().strip('"')

async def generate_chapter_titles(prompt: str, num_chapters: int, data_context: dict) -> list[str]:
    titles_prompt = build_title_generation_prompt(prompt, "chapter_list", num_chapters, data_context)
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": titles_prompt}],
        temperature=0.7, max_tokens=60 * num_chapters
    )
    content = response.choices[0].message.content
    titles = re.findall(r'^\d+\.\s*(.*)', content, re.MULTILINE)
    return titles if titles else [f"Chapter {i+1}" for i in range(num_chapters)]

async def generate_chapter_section(prompt: str, title: str, summary: str, context: dict, words: int) -> str:
    content_prompt = build_chapter_section_prompt(prompt, title, summary, context, words)
    response = await openai.chat.completions.create(
        model=MODEL_TEXT, messages=[{"role": "user", "content": content_prompt}],
        temperature=0.75, max_tokens=MAX_TOKENS_PER_SECTION
    )
    return response.choices[0].message.content.strip()

async def summarize_section(text: str) -> str:
    summary_prompt = build_summarization_prompt(text)
    try:
        response = await openai.chat.completions.create(
            model=MODEL_TEXT, messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2, max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return text[:300] + "..."

async def generate_content_block(prompt: str, title: str, context: dict, word_target: int) -> str:
    print(f"--- Generating content for: '{title}' (Target: {word_target} words) ---")
    num_sections = max(1, round(word_target / WORDS_PER_SECTION_TARGET))
    parts = []
    summary = f"The section is '{title}'. Set the scene and begin the narrative."
    for i in range(num_sections):
        print(f"  - Generating part {i+1}/{num_sections}...")
        section_text = await generate_chapter_section(prompt, title, summary, context, WORDS_PER_SECTION_TARGET)
        parts.append(section_text)
        if i < num_sections - 1:
            print(f"  - Summarizing part {i+1} for continuity...")
            summary = await summarize_section(section_text)
        print("  - Pausing for 4 seconds to respect API rate limits...")
        await asyncio.sleep(4)
    print(f"--- Finished content for: '{title}' ---")
    return "\n\n".join(parts)

# --- Main Orchestration ---
def calculate_book_parameters(num_pages: int) -> tuple[int, int]:
    WORDS_PER_PAGE = 250
    AVG_WORDS_PER_CHAPTER = 10000
    FIXED_PAGES = 1 + 4 + 4 + 1 + 1 + 1 + 2 + 1 + 1 + 1 + 2 + 1 + 1 # Total fixed pages before chapters

    # Estimate chapters to account for chapter title pages
    temp_content_pages = num_pages - FIXED_PAGES
    estimated_chapters = max(1, round((temp_content_pages * WORDS_PER_PAGE) / AVG_WORDS_PER_CHAPTER))
    
    content_pages_for_chapters = max(1, num_pages - FIXED_PAGES - estimated_chapters)
    total_words_needed = content_pages_for_chapters * WORDS_PER_PAGE
    chapters_needed = estimated_chapters
    target_words_per_chapter = int(total_words_needed / chapters_needed) if chapters_needed > 0 else 0
    
    print(f"Request for {num_pages} pages -> Content pages: {content_pages_for_chapters} -> Aiming for {chapters_needed} chapters of ~{target_words_per_chapter} words each.")
    return chapters_needed, target_words_per_chapter

async def generate_user_prompt_driven_book(prompt: str, num_pages: int) -> dict:
    chapters_needed, target_words_per_chapter = calculate_book_parameters(num_pages)
    
    print("Selecting relevant SWAPI data based on prompt...")
    data_context = await select_book_data_context(prompt)
    
    print("Generating book components in parallel...")
    prologue_word_target = int(2 * 250)
    epilogue_word_target = int(1 * 250)
    
    tasks = {
        "image": generate_book_image(prompt, data_context),
        "prologue": generate_content_block(prompt, "Prologue", data_context, prologue_word_target),
        "epilogue": generate_content_block(prompt, "Epilogue", data_context, epilogue_word_target),
        "titles": generate_chapter_titles(prompt, chapters_needed, data_context)
    }
    
    results = await asyncio.gather(*tasks.values())
    image_path, prologue_text, epilogue_text, chapter_titles = results
    
    final_titles = chapter_titles[:chapters_needed]
    
    chapter_texts = []
    print("\n--- Starting Sequential Chapter Content Generation ---")
    for i, title in enumerate(final_titles):
        chapter_heading = f"Chapter - {i+1}: {title}"
        print(f"\n[Generating {chapter_heading}]")
        chapter_text = await generate_content_block(prompt, chapter_heading, data_context, target_words_per_chapter)
        chapter_texts.append({"heading": chapter_heading, "content": chapter_text})

    try:
        with open("preface.txt", "r", encoding='utf-8') as f: preface_text = f.read()
    except FileNotFoundError:
        preface_text = "Preface file not found."

    return {
        "swapi_call_text": f"User Prompt: {prompt}",
        "swapi_json_output": json.dumps(data_context, indent=4),
        "image_path": image_path,
        "preface_text": preface_text,
        "prologue_text": prologue_text,
        "epilogue_text": epilogue_text,
        "chapters": chapter_texts,
    }