import os
import re
import json
from typing import Dict, List
from rag.util.parse.text_parse import remove_deleted_text, _fixed_size_chunk, _token_count, _compress_numbers

local_path = os.path.dirname(os.path.abspath(__file__))
def chunk_bill(bill_text:str, max_tokens:int=1000, bill_name:str=None) -> List[Dict]:

    cleaned_text = remove_deleted_text(bill_text)
    # This pattern allows the section header to span multiple lines and is resilient to the case where the next section starts immediately (no blank lines required).
    section_pattern = re.compile(

        # Previous matching pattern: r"(^\s*SEC\.\s*(\d+)\.[\s\S]*?(?=\n\s*\n))([\s\S]*?)(?=^\s*SEC\.\s*\d+\.|\Z)"
        r"(^\s*SEC\.\s*(\d+)\..*?)(?:\n|$)([\s\S]*?)(?=^\s*SEC\.\s*\d+\.|\Z)",
        re.MULTILINE
    )
    matches = list(section_pattern.finditer(cleaned_text))

    section_titles, section_texts = [], []
    for m in matches:
        section_title = m.group(1).strip()
        section_body = m.group(3)
        section_body = section_body.strip()

        section_titles.append(section_title)
        section_texts.append(section_title + "\n" + section_body if section_body else section_title)

    section_text_chunks = []
    section_title_chunks = []

    # This pattern right here is to detect if a section is composed of an amendment to an already existing section in public law
    insertion_pattern = re.compile(
        r"""
        (?ixm)
        # 1) Check for statements like: "Section X of [Act] ... is amended--"
        \b(?:section|subsection|paragraph|subparagraph)\b
        [\s\S]{0,200}?
        \bof\b
        [\s\S]{0,200}?
        \bis\s+amended\b
        (?:\s*(?:--|—))?
        |
        # 2) Same but with explicit 'by <operation>' (e.g. "by striking out...")
        \b(?:section|subsection|paragraph|subparagraph)\b
        [\s\S]{0,200}?
        \bis\s+amended\s+by\b
        [\s\S]{0,200}?
        |
        # 3) List-item level operations after an "is amended--" lead-in
        \b(?:in\s+(?:section|subsection|paragraph|subparagraph)\b[\s\S]{0,60}?,\s*)?
        \bby\s+(?:striking|inserting|adding|redesignating)\b
        [\s\S]{0,200}?
        (?:\bafter\b|\bbefore\b|\bat\s+the\s+end\b|\bas\s+follows\b)?
        """,
        re.IGNORECASE | re.MULTILINE | re.VERBOSE,
    )

    insertion_map = {} # maps a section number to a boolean indicating if it is an insertion
    section_number_re = re.compile(r"SEC\.\s*(\d+)")
    for sec_text in section_texts:
        sec_header = sec_text.split('\n', 1)[0]
        sec_num_match = section_number_re.search(sec_header)
        sec_num = int(sec_num_match.group(1)) if sec_num_match else -1
        is_insertion = insertion_pattern.search(sec_text, endpos=len(sec_header) + 500)

        if is_insertion:
            insertion_map[sec_num] = is_insertion

        sec_text = sec_text[len(sec_header):].strip()

        # Save each section's text to a JSON file for later editing.
        # We'll collect all sections in a list and write them out once at the end.
        if 'all_sections_for_json' not in locals():
            all_sections_for_json = []
        all_sections_for_json.append({
            "section": str(sec_num) if sec_num != -1 else sec_header,
            "text": sec_header + "\n" + sec_text,
        })
        # At the end of the outermost loop (after all sections processed), write to file.
        # (This should be moved outside the loop in the main function, but for inline use, check if last section)
        if len(all_sections_for_json) == len(section_texts):
            sections_file_path = f"{local_path}/../../data/tmp_sections/sections_for_edit.json"

            # Load existing sections dict or create new one
            try:
                with open(sections_file_path, "r", encoding="utf-8") as f:
                    all_bills_sections = json.load(f)
                    # Handle old format (list) - convert to dict
                    if isinstance(all_bills_sections, list):
                        all_bills_sections = {}
            except (FileNotFoundError, json.JSONDecodeError):
                all_bills_sections = {}

            # Store sections under bill_name key if provided
            if bill_name:
                all_bills_sections[bill_name] = all_sections_for_json
            else:
                # Fallback: store under "default" key
                all_bills_sections["default"] = all_sections_for_json

            # Write back the entire dict
            with open(sections_file_path, "w", encoding="utf-8") as f:
                json.dump(all_bills_sections, f, ensure_ascii=False, indent=2)
                
        sub_chunks = _fixed_size_chunk(sec_text, max_tokens, overlap=max_tokens*0.05)
        for i, chunk_text in enumerate(sub_chunks):
            section_text_chunks.append({
                "type": "text",
                "text": sec_header + "\n" + chunk_text,
                "meta": {"kind": "text", "section": sec_header, "is_insertion": True if sec_num in insertion_map else False},
            })
    tmp_text, tmp_token_total, tmp_sections = "", 0, []
    for title in section_titles:
        tokens = _token_count(title)
        
        sec_num_match = section_number_re.search(title)
        sec_num = int(sec_num_match.group(1)) if sec_num_match else -1

        if tmp_token_total + tokens > max_tokens and tmp_text:
            section_title_chunks.append({
                "type": "title",
                "text": tmp_text.strip(),
                "meta": {"kind": "title", "section_range": _compress_numbers(tmp_sections)},
            })
            tmp_text, tmp_token_total, tmp_sections = "", 0, []
        
        tmp_text += title + "\n\n"
        tmp_token_total += tokens

        if sec_num != -1:
            tmp_sections.append(sec_num)
    
    if tmp_text:
        section_title_chunks.append({
            "type": "title",
            "text": tmp_text.strip(),
            "meta": {"kind": "title", "section_range": _compress_numbers(tmp_sections)},
        })
    
    return section_title_chunks, section_text_chunks