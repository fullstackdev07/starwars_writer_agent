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
WORDS_PER_CHAPTER_TARGET = 10000
WORDS_PER_SECTION_TARGET = 750 # The size of each chunk we generate for a chapter
MAX_TOKENS_PER_SECTION = 1200 # A safe buffer for the section words

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
        
        # Now, retrieve the full data objects for the selected names
        book_context = {}
        for category, names in selected_names.items():
            if category in ALL_SWAPI_DATA:
                book_context[category] = [
                    item for item in ALL_SWAPI_DATA[category] if item.get('name') in names or item.get('title') in names
                ]
        return book_context
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing AI data selection, falling back to random selection. Error: {e}")
        # Fallback to random selection if AI fails
        return {
            "people": random.sample(ALL_SWAPI_DATA.get("people", []), min(len(ALL_SWAPI_DATA.get("people", [])), 5)),
            "planets": random.sample(ALL_SWAPI_DATA.get("planets", []), min(len(ALL_SWAPI_DATA.get("planets", [])), 3)),
            "starships": random.sample(ALL_SWAPI_DATA.get("starships", []), min(len(ALL_SWAPI_DATA.get("starships", [])), 2)),
        }

# --- Title and Chapter Title Generation ---
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
async def generate_chapter_section(prompt: str, chapter_title: str, previous_section_summary: str, data_context: dict) -> str:
    """Generates a single section of a chapter, ensuring continuity."""
    content_prompt = build_chapter_section_prompt(prompt, chapter_title, previous_section_summary, data_context, WORDS_PER_SECTION_TARGET)
    
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
        # Fallback if summarization fails
        return section_text[:300] + "..."


async def generate_single_chapter_content(prompt: str, chapter_title: str, data_context: dict) -> str:
    """
    Generates the full 10,000-word content for a single chapter by chaining sections.
    """
    print(f"--- Generating Chapter: '{chapter_title}' (Target: {WORDS_PER_CHAPTER_TARGET} words) ---")
    num_sections = round(WORDS_PER_CHAPTER_TARGET / WORDS_PER_SECTION_TARGET)
    chapter_parts = []
    previous_summary = "The chapter begins. Introduce the setting and main characters for this chapter."

    for i in range(num_sections):
        print(f"  - Generating section {i+1}/{num_sections}...")
        section_text = await generate_chapter_section(prompt, chapter_title, previous_summary, data_context)
        chapter_parts.append(section_text)

        if i < num_sections - 1:
            print(f"  - Summarizing section {i+1} for continuity...")
            previous_summary = await summarize_section(section_text)

        # --- THIS IS THE UPDATED LINE ---
        # Increased pause to 5 seconds. This is a more conservative value to
        # ensure we never hit the Tokens-Per-Minute (TPM) limit.
        print("  - Pausing for 5 seconds to respect API rate limits...")
        await asyncio.sleep(5)
        # -----------------------------------------------------------

    full_chapter = "\n\n".join(chapter_parts)
    print(f"--- Finished Chapter: '{chapter_title}' ---")
    return full_chapter

# --- Main Orchestration ---
def calculate_book_parameters(num_pages: int) -> int:
    """Calculates the number of chapters needed to fill the page count."""
    WORDS_PER_PAGE = 275  # Standard estimate
    total_words_needed = num_pages * WORDS_PER_PAGE
    chapters_needed = max(1, round(total_words_needed / WORDS_PER_CHAPTER_TARGET))
    
    print(f"Request for {num_pages} pages -> Aiming for {chapters_needed} chapters of ~{WORDS_PER_CHAPTER_TARGET} words each.")
    return chapters_needed

async def generate_user_prompt_driven_book(prompt: str, num_pages: int, writing_sample: str = "") -> str:
    """
    Top-level function to orchestrate the entire data-driven book generation process.
    """
    # Step 1: Calculate the exact number of chapters needed.
    chapters_needed = calculate_book_parameters(num_pages)
    
    # Step 2: Use AI to select a relevant "cast" from local data.
    print("Selecting relevant SWAPI data based on prompt...")
    data_context = await select_book_data_context(prompt)
    
    # Step 3: Ask the AI to generate chapter titles.
    print(f"Generating {chapters_needed} custom chapter titles...")
    all_generated_titles = await generate_chapter_titles(prompt, chapters_needed, data_context)
    print("AI returned these titles (raw):", all_generated_titles)
    
    # --- THIS IS THE CRITICAL FIX THAT WAS MISSING ---
    # We MUST enforce the chapter count we calculated.
    # No matter what the AI gives us, we only take the number we need.
    final_titles = all_generated_titles[:chapters_needed]
    print(f"ENFORCING LIMIT. Final titles to be generated: {final_titles}")
    # --------------------------------------------------

    # Step 4: Generate content ONLY for the final, limited list of titles.
    tasks = [
        generate_single_chapter_content(prompt, title, data_context)
        for title in final_titles
    ]
    all_chapter_texts = await asyncio.gather(*tasks)
    
    # Step 5: Assemble the final book text.
    book_content = []
    for i, title in enumerate(final_titles):
        book_content.append(f"## {title}\n\n{all_chapter_texts[i]}")
        
    return "\n\n".join(book_content)