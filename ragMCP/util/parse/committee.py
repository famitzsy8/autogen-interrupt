import yaml, re, os

local_path = os.path.dirname(os.path.abspath(__file__))

def _get_committee_code(name: str) -> dict:
    debug_messages = []
    path = os.path.join(local_path, "../../data/committees/committees_standing.yaml")
    debug_messages.append(f"Loading YAML from: {path}")

    with open(path, "r") as f:
        committees = yaml.safe_load(f)

    raw = name.strip()
    debug_messages.append(f"Raw input: {raw}")

    if "house" not in raw.lower() and "senate" not in raw.lower():
        debug_messages.append("Input is missing 'House' or 'Senate' — cannot determine chamber.")
        return {"committee_code": None, "debug": debug_messages}

    # 1) Subcommittee form
    sub_re = re.compile(
        r"^Subcommittee on (.+) under the (House|Senate) Committee on (.+)$",
        re.IGNORECASE
    )
    m = sub_re.match(raw)
    if m:

        sub_name, chamber, parent_main = m.groups()
        parent_full = f"{chamber} Committee on {parent_main}".strip().lower()

        sub_name = sub_name.strip().lower()
        debug_messages.append(f"Subcommittee detected: parent='{parent_full}', sub='{sub_name}'")

        for c in committees:
            if c.get("name", "").strip().lower() == parent_full:
                parent_id = c.get("thomas_id")
                debug_messages.append(f"Parent ID found: {parent_id}")

                for sub in c.get("subcommittees", []):

                    if sub.get("name", "").strip().lower() == sub_name:

                        sub_id = sub.get("thomas_id")
                        code = f"{parent_id}{sub_id}"
                        debug_messages.append(f"Subcommittee ID found: {sub_id} -> code: {code}")

                        return {"committee_code": code, "debug": debug_messages}

        debug_messages.append("Parent committee or subcommittee not found.")
        return {"committee_code": None, "debug": debug_messages}

    # 2) Main committee form
    main_re = re.compile(r"^(House|Senate) Committee on (.+)$", re.IGNORECASE)
    m = main_re.match(raw)

    if m:
        
        chamber, main_body = m.groups()
        full = f"{chamber} Committee on {main_body}".strip().lower()
        debug_messages.append(f"Main committee detected: {full}")

        for c in committees:

            if c.get("name", "").strip().lower() == full:

                base_id = c.get("thomas_id")
                code = f"{base_id}01"

                debug_messages.append(f"Committee code found: {code}")
                return {"committee_code": code, "debug": debug_messages}

        debug_messages.append("Main committee not found.")
        return {"committee_code": None, "debug": debug_messages}

    debug_messages.append("Input did not match any known committee format.")
    return {"committee_code": None, "debug": debug_messages}
