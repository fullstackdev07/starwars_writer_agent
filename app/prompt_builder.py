def build_flexible_prompt(user_prompt: str, character_info: dict | None) -> str:
    with open("app/writing_sample.txt", "r", encoding="utf-8") as f:
        tone = f.read()

    base_prompt = f"""
You are a creative Star Wars storyteller. Use the following tone and style:
---
{tone}
---

Based on the user's input, generate a rich, immersive, emotional story.

User Prompt:
"{user_prompt}"

"""

    if character_info:
        base_prompt += f"""

Here is supporting factual data to include if helpful:
- Name: {character_info.get("name", "Unknown")}
- Birth Year: {character_info.get("birth_year", "Unknown")}
- Homeworld: {character_info.get("homeworld", "Unknown")}
- Height: {character_info.get("height", "Unknown")}
- Hair Color: {character_info.get("hair_color", "Unknown")}
- Eye Color: {character_info.get("eye_color", "Unknown")}
"""

    base_prompt += "\nWrite the story in full. Add chapters if appropriate. Do not ask the user anything back."

    return base_prompt

def build_flexible_prompt(user_input: str, character_info: dict | None = None) -> str:
    if character_info:
        return f"{user_input}. Here is some reference info: {character_info}"
    return user_input

def default_chapter_titles() -> list[str]:
    return [
        "Early Life and Origins",
        "Formative Training",
        "Rise to Power",
        "Major Conflicts",
        "Turning Point",
        "The Great Betrayal",
        "Redemption Arc",
        "Legacy and Influence"
    ]