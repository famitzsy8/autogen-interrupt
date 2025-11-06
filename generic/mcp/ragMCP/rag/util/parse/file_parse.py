import os
import yaml
import json

local_path = os.path.dirname(os.path.abspath(__file__))

def load_prompts():
    with open(f"{local_path}/../../config/prompts.yaml", "r") as f:
        prompts = yaml.safe_load(f)
    return prompts

# PREVIOUSLY: getSectionText
def get_section_text(section_number: str, bill_name: str = None) -> str:
    """
    Given a section number and bill_name, return the section text from the JSON file.
    The JSON file is now a dict where keys are bill names (e.g., "s1593-116")
    and values are lists of dicts with keys "section" and "text".
    """
    path = f"{local_path}/../../data/tmp_sections/sections_for_edit.json"

    try:
        with open(path, "r", encoding="utf-8") as f:
            all_bills_sections = json.load(f)

        # Handle dict structure (new format)
        if isinstance(all_bills_sections, dict):
            # Use bill_name if provided, otherwise try "default"
            sections = all_bills_sections.get(bill_name if bill_name else "default", [])
        else:
            # Handle old list format (backward compatibility)
            sections = all_bills_sections

        for entry in sections:
            if entry.get("section") == section_number:
                return entry.get("text", "")

    except Exception as e:
        print(f"Error reading section text: {e}")
    return ""
