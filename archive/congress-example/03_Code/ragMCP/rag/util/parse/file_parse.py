import os
import yaml
import json

local_path = os.path.dirname(os.path.abspath(__file__))

def load_prompts():
    with open(f"{local_path}/../../config/prompts.yaml", "r") as f:
        prompts = yaml.safe_load(f)
    return prompts

# PREVIOUSLY: getSectionText
def get_section_text(section_number: str) -> str:
    """
    Given a section number as a string, return the section text from the JSON file.
    The JSON file is expected to be a list of dicts with keys "section" and "text".
    """
    path = f"{local_path}/../../data/tmp_sections/sections_for_edit.json"

    try:
        with open(path, "r", encoding="utf-8") as f:
            sections = json.load(f)
        for entry in sections:
            if entry.get("section") == section_number:
                return entry.get("text", "")
                
    except Exception as e:
        print(f"Error reading section text: {e}")
    return ""
