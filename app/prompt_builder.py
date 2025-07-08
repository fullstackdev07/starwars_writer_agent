# app/prompt_builder.py
import json

def build_data_selection_prompt(user_prompt: str, all_data: dict) -> str:
    """Builds a prompt to ask the AI to select relevant entities from the SWAPI data."""
    data_summary = {
        "people": [p.get('name') for p in all_data.get('people', [])],
        "planets": [p.get('name') for p in all_data.get('planets', [])],
        "starships": [s.get('name') for s in all_data.get('starships', [])],
        "films": [f.get('title') for f in all_data.get('films', [])],
    }
    return f"""
Based on the user's story prompt, select a small, coherent set of entities from the provided JSON data. This will be the "cast" for the entire novel. Choose a few main characters, a primary setting (planet), and a few relevant starships.
USER PROMPT: "{user_prompt}"
AVAILABLE DATA:
{json.dumps(data_summary, indent=2)}
Your task:
Respond with a JSON object containing the *names* of the entities to use. The JSON object should have keys: "people", "planets", "starships".
Example Response:
{{
  "people": ["Luke Skywalker", "Darth Vader", "Leia Organa"],
  "planets": ["Tatooine", "Alderaan"],
  "starships": ["X-wing", "TIE Advanced x1"]
}}
"""

def build_title_generation_prompt(user_prompt: str, title_type: str, num_chapters: int = 0, data_context: dict = None) -> str:
    """Builds a prompt for generating a book title or a list of chapter titles."""
    context_str = ""
    if data_context:
        context_str = f"The story will feature: {', '.join([p['name'] for p in data_context.get('people', [])])} on the planet {', '.join([p['name'] for p in data_context.get('planets', [])])}."
    if title_type == "book":
        return f"""
Generate a short, creative, and evocative book title for a Star Wars story about: '{user_prompt}'.
{context_str}
The title should sound like a real novel. Do not include 'Star Wars:' in the title itself. Only return the title, with no extra text or quotation marks.
"""
    elif title_type == "chapter_list":
        return f"""
I am writing a {num_chapters}-chapter Star Wars novel about: '{user_prompt}'.
{context_str}
Please generate a list of {num_chapters} creative and sequential chapter titles for this story. Return them as a numbered list (e.g., '1. The Awakening', '2. A Fading Hope').
"""

def build_chapter_section_prompt(user_prompt: str, chapter_title: str, previous_section_summary: str, data_context: dict, word_target: int) -> str:
    """Builds the main prompt for generating a single section of a chapter's content."""
    return f"""
You are a novelist writing a Star Wars story in the second person ("You feel...", "You see...").
Your task is to write a single, detailed section of the novel.

CRITICAL INSTRUCTION: You MUST base your writing *exclusively* on the data provided in the "DATA CONTEXT" section. Do not invent new characters, planets, or major technologies. Weave the provided data into a narrative.

STORY THEME: "{user_prompt}"
CURRENT SECTION: This section is part of '{chapter_title}'.
CONTINUITY: The previous part of the story concluded with the following events: "{previous_section_summary}"

DATA CONTEXT (Your only source of truth for names, places, and specs):
---
{json.dumps(data_context, indent=2)}
---

Your task:
Write the next section of the story, continuing from the summary. Make it detailed, descriptive, and approximately {word_target} words long.
Begin writing the content directly. Do not repeat the chapter title.
"""

def build_summarization_prompt(section_text: str) -> str:
    """Builds a prompt to summarize a generated section for continuity."""
    return f"""
Summarize the following block of text in 2-3 sentences. Focus on the key actions, character movements, and plot developments. This summary will be used as a continuity guide for the next block of writing.

TEXT TO SUMMARIZE:
---
{section_text}
---
"""

def build_image_generation_prompt(user_prompt: str, data_context: dict) -> str:
    """Builds a descriptive prompt for the DALL-E 3 image generator."""
    characters = [p.get('name') for p in data_context.get('people', [])]
    planets = [p.get('name') for p in data_context.get('planets', [])]
    starships = [s.get('name') for s in data_context.get('starships', [])]
    character_str = f"featuring the characters: {', '.join(characters)}" if characters else ""
    planet_str = f"set on the planet {', '.join(planets)}" if planets else ""
    starship_str = f"with notable starships like {', '.join(starships)}" if starships else ""
    return f"""
A dramatic and evocative digital painting in the style of classic Star Wars concept art. The scene is cinematic, with a focus on atmosphere and scale.
The overall story is about: '{user_prompt}'.
The scene should incorporate the following elements: {character_str} {planet_str} {starship_str}.
The mood is gritty and epic, with realistic textures and dramatic lighting. Do NOT include any text, titles, or logos in the image.
"""