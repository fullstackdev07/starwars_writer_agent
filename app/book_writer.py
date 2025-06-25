# app/book_writer.py

from openai import AsyncOpenAI
import os
import asyncio
import re
import json
import random
from app.prompt_builder import build_chapter_section_prompt, build_summarization_prompt, build_title_generation_prompt, build_data_selection_prompt
from dotenv import load_dotenv

load_dotenv()

openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4-1106-preview"

# Constants for chapter section generation
WORDS_PER_SECTION_TARGET = 750
MAX_TOKENS_PER_SECTION = 1200

# --- Data Loading ---
def load_all_swapi_data():
    """Loads all data from the swapi_data JSON files."""
    data = {}
    data_dir = "swapi_data"
    if not os.path.exists(data_dir):
        raise FileNotFoundError("The 'swapi_data' directory was not found. Please run the fetch_swapi_data.py script first.")
    
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            category = filename.replace(".json", "")
            with open(os.path.join(data_dir, filename), "r") as f:
                data[category] = json.load(f)
    return data

ALL_SWAPI_DATA = load_all_swapi_data()
print("SWAPI data loaded successfully.")


# --- Data Selection ---
async def select_book_data_context(prompt: str) -> dict:
    """Uses the AI to select a relevant 'cast' of characters, planets, etc., for the book."""
    selection_prompt = build_data_selection_prompt(prompt, ALL_SWAPI_DATA)
    
    response = await openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": selection_prompt}],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    try:
        selected_names = json.loads(response.choices[0].message.content)
        print(f"AI selected data context: {selected_names}")
        
        book_context = {}
        for category, names in selected_names.items():
            if category in ALL_SWAPI_DATA:
                book_context[category] = [
                    item for item in ALL_SWAPI_DATA[category] if item.get('name') in names or item.get('title') in names
                ]
        return book_context
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing AI data selection, falling back to random selection. Error: {e}")
        return {
            "people": random.sample(ALL_SWAPI_DATA.get("people", []), min(len(ALL_SWAPI_DATA.get("people", [])), 5)),
            "planets": random.sample(ALL_SWAPI_DATA.get("planets", []), min(len(ALL_SWAPI_DATA.get("planets", [])), 3)),
            "starships": random.sample(ALL_SWAPI_DATA.get("starships", []), min(len(ALL_SWAPI_DATA.get("starships", [])), 2)),
        }


# --- Title Generation ---
async def generate_book_title(prompt: str) -> str:
    """Generates a creative book title based on the user's prompt."""
    title_prompt = build_title_generation_prompt(prompt, "book")
    response = await openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": title_prompt}],
        temperature=0.8,
        max_tokens=20
    )
    return response.choices[0].message.content.strip().strip('"')

async def generate_chapter_titles(prompt: str, num_chapters: int, data_context: dict) -> list[str]:
    """Generates a list of chapter titles for the book using the selected data context."""
    titles_prompt = build_title_generation_prompt(prompt, "chapter_list", num_chapters, data_context)
    response = await openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": titles_prompt}],
        temperature=0.7,
        max_tokens=60 * num_chapters
    )
    content = response.choices[0].message.content
    titles = re.findall(r'^\d+\.\s*(.*)', content, re.MULTILINE)
    return titles if titles else [f"Chapter {i+1}" for i in range(num_chapters)]


# --- Chained Chapter Generation Logic ---
async def generate_chapter_section(prompt: str, chapter_title: str, previous_section_summary: str, data_context: dict, word_target: int) -> str:
    """Generates a single section of a chapter."""
    content_prompt = build_chapter_section_prompt(prompt, chapter_title, previous_section_summary, data_context, word_target)
    
    response = await openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": content_prompt}],
        temperature=0.75,
        max_tokens=MAX_TOKENS_PER_SECTION
    )
    return response.choices[0].message.content.strip()

async def summarize_section(section_text: str) -> str:
    """Summarizes a section of text to be used as context for the next section."""
    summary_prompt = build_summarization_prompt(section_text)
    try:
        response = await openai.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return section_text[:300] + "..."

async def generate_single_chapter_content(prompt: str, chapter_title: str, data_context: dict, target_word_count: int) -> str:
    """
    Generates the full content for a single chapter by chaining sections.
    The number of sections is dynamic based on the target_word_count.
    """
    print(f"--- Generating Section: '{chapter_title}' (Target: {target_word_count} words) ---")
    num_sections = max(1, round(target_word_count / WORDS_PER_SECTION_TARGET))
    chapter_parts = []
    
    # Give a slightly different starting point for Prologue/Epilogue vs. a numbered chapter.
    if "chapter" in chapter_title.lower():
        previous_summary = "The chapter begins. Re-establish the scene or continue from the previous chapter's events."
    else:
        previous_summary = f"This is the {chapter_title}. Set the stage for the entire story or provide a concluding thought."

    for i in range(num_sections):
        print(f"  - Generating part {i+1}/{num_sections}...")
        section_text = await generate_chapter_section(prompt, chapter_title, previous_summary, data_context, WORDS_PER_SECTION_TARGET)
        chapter_parts.append(section_text)

        if i < num_sections - 1:
            print(f"  - Summarizing part {i+1} for continuity...")
            previous_summary = await summarize_section(section_text)
        
        print("  - Pausing for 4 seconds to respect API rate limits...")
        await asyncio.sleep(4)

    full_chapter = "\n\n".join(chapter_parts)
    print(f"--- Finished Section: '{chapter_title}' ---")
    return full_chapter


# --- Main Orchestration ---
def calculate_book_parameters(num_pages: int) -> tuple[int, int]:
    """
    Calculates parameters for the *numbered chapters*, reserving pages for
    a Prologue and Epilogue.
    """
    WORDS_PER_PAGE = 215
    AVG_WORDS_PER_CHAPTER = 8000
    PAGES_FOR_PROLOGUE_EPILOGUE = 6 # Reserve 3 pages for each

    # Subtract reserved pages from the total to get pages for main chapters
    content_pages_for_chapters = max(1, num_pages - PAGES_FOR_PROLOGUE_EPILOGUE)

    total_words_needed = content_pages_for_chapters * WORDS_PER_PAGE
    chapters_needed = max(1, round(total_words_needed / AVG_WORDS_PER_CHAPTER))
    target_words_per_chapter = int(total_words_needed / chapters_needed)
    
    print(f"Request for {num_pages} pages -> "
          f"Reserving {PAGES_FOR_PROLOGUE_EPILOGUE} pages for Prologue/Epilogue. "
          f"Aiming for {chapters_needed} chapters of ~{target_words_per_chapter} words each.")
    
    return chapters_needed, target_words_per_chapter

async def generate_user_prompt_driven_book(prompt: str, num_pages: int, writing_sample: str = "") -> str:
    """
    Top-level function that now builds the book with a Prologue and Epilogue.
    """
    chapters_needed, target_words_per_chapter = calculate_book_parameters(num_pages)
    PROLOGUE_EPILOGUE_WORD_TARGET = 1200 # Fixed shorter length for these sections
    
    print("Selecting relevant SWAPI data based on prompt...")
    data_context = await select_book_data_context(prompt)
    
    # --- PROLOGUE GENERATION ---
    print("\n--- Starting Prologue Generation ---")
    prologue_text = await generate_single_chapter_content(
        prompt, "Prologue", data_context, PROLOGUE_EPILOGUE_WORD_TARGET
    )
    
    # --- NUMBERED CHAPTERS GENERATION ---
    print(f"\n--- Starting Generation for {chapters_needed} Numbered Chapters ---")
    final_titles = []
    chapter_texts = []
    if chapters_needed > 0:
        all_generated_titles = await generate_chapter_titles(prompt, chapters_needed, data_context)
        final_titles = all_generated_titles[:chapters_needed]
        print(f"Final titles to be generated: {final_titles}")
        
        for i, title in enumerate(final_titles):
            print(f"\n[Generating Chapter {i+1}/{len(final_titles)}: '{title}']")
            chapter_text = await generate_single_chapter_content(
                prompt, f"Chapter - {i+1}: {title}", data_context, target_words_per_chapter
            )
            chapter_texts.append(chapter_text)

    # --- EPILOGUE GENERATION ---
    print("\n--- Starting Epilogue Generation ---")
    epilogue_text = await generate_single_chapter_content(
        prompt, "Epilogue", data_context, PROLOGUE_EPILOGUE_WORD_TARGET
    )
    
    # --- ASSEMBLE THE FINAL BOOK ---
    print("\n--- Assembling Final Book Text ---")
    book_content = [f"## Prologue\n\n{prologue_text}"]
    for i, title in enumerate(final_titles):
        heading = f"Chapter - {i+1}: {title}"
        book_content.append(f"## {heading}\n\n{chapter_texts[i]}")
    book_content.append(f"## Epilogue\n\n{epilogue_text}")
    
    return "\n\n".join(book_content)