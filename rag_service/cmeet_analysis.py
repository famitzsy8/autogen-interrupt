# Hier analyseeren we die committee meetings van die Kongress
import sys, os
sys.path.append(os.getcwd() + "/rag_service")
from util.parse_util import _call_and_parse, __extract_text_from_html_url
from requests.exceptions import HTTPError
import json

NUM_MEETINGS = 1000
CONGRESS = "116"
CHAMBER = "senate"

def get_meetings(congress:str, chamber:str, limit=250):
    """
    congress: "115"
    chamber: "house/senate"
    """
    args = {
        "congress": congress,
        "chamber": chamber
    }
    endpoint = "committee-meeting/{congress}/{chamber}"

    roots = _call_and_parse(args, endpoint, multiple_pages=True)
    items = []
    for root in roots:
        for item in root.findall(".//committeeMeetings/item"):
            data = {child.tag: child.text.strip() for child in item}
            items.append(data)
    return items[:limit]

def getTranscriptFromMeeting(url: str) -> dict:
    """
    Given the full API URL of a committee-meeting, fetches the meeting XML,
    pulls out the hearingTranscript, and returns a dictionary containing the
    meeting title and the URL to the 'Formatted Text' (HTM) transcript.

    Returns:
        A dictionary in the format {meeting_title: htm_transcript_url}.

    Raises:
        ValueError: If the meeting is closed, or if a transcript cannot be found.
        requests.exceptions.HTTPError: If there is an issue fetching data from the API.
    """
    endpoint = url.removeprefix("https://api.congress.gov/v3/")\
                  .removesuffix("?format=xml")

    meeting_root = _call_and_parse({}, endpoint)

    title = meeting_root.findtext(".//title")
    if title is None:
        title = "Title not found"

    if "closed" in title.lower():
        raise ValueError(f"Meeting is closed: {title}")

    ht_item = meeting_root.find(".//hearingTranscript/item")
    if ht_item is None:
        raise ValueError(f"No hearing transcript found for meeting: {title}")

    return _get_hearing_text(title, ht_item.findtext("url", "").strip())


def _get_hearing_text(title, hearing_url: str) -> dict:
    hearing_endpoint = hearing_url.removeprefix("https://api.congress.gov/v3/")\
                                  .removesuffix("?format=xml")

    hearing_root = _call_and_parse({}, hearing_endpoint)
    for fmt in hearing_root.findall(".//formats/item"):
        if fmt.findtext("type", "").strip().lower() == "formatted text":
            return {title: fmt.findtext("url", "").strip()}

def extract_and_process_meetings(meetings_to_process: list, total_meetings: int) -> tuple[dict, int, int, list]:
    """
    Extracts transcripts from a list of meeting URLs.
    Returns a dictionary of texts and statistics about the extraction process.
    """
    texts = {}
    processed_count = 0
    closed_count = 0
    unknown_count = 0
    unknown_titles = []

    for m in meetings_to_process:
        url = m["url"]
        try:
            transcript_info = getTranscriptFromMeeting(url)
            title, transcriptLink = next(iter(transcript_info.items()))
            text = __extract_text_from_html_url(transcriptLink)
            
            key = url.removeprefix("https://api.congress.gov/v3/committee-meeting/")
            key = key.removesuffix("?format=xml")
            key_parts = key.split("/")
            congress, chamber, eventid = key_parts[0], key_parts[1], key_parts[2]
            
            if congress not in texts:
                texts[congress] = {}
            if chamber not in texts[congress]:
                texts[congress][chamber] = {}
            
            texts[congress][chamber][eventid] = text
            processed_count += 1
            print(f"Processed {processed_count} of {total_meetings}")

        except ValueError as e:
            if "closed" in str(e).lower():
                closed_count += 1
            else:
                unknown_count += 1
                try:
                    title_from_exc = str(e).split(":", 1)[1].strip()
                    unknown_titles.append(title_from_exc)
                except IndexError:
                    unknown_titles.append(f"Unknown error for URL {url}: {e}")
        except HTTPError as e:
            print(f"HTTP error for {url}: {e}")
            continue
    
    return texts, closed_count, unknown_count, unknown_titles

def save_transcripts(texts: dict, output_path: str):
    """Saves the extracted transcripts to a JSON file."""
    with open(output_path, "w") as f:
        json.dump(texts, f, indent=2)
    print(f"Transcripts saved to {output_path}")

def analyze_token_count(file_path: str):
    """Analyzes and prints the token count of a file."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        with open(file_path, "r") as f:
            content = f.read()
        token_count = len(enc.encode(content))
        print(f"Total token count (tiktoken): {token_count}")
    except ImportError:
        print("tiktoken not installed, falling back to word count.")
        with open(file_path, "r") as f:
            content = f.read()
        word_count = len(content.split())
        print(f"Rough word count: {word_count}")

def main():
    """
    Main function to fetch, process, and analyze committee meetings.
    """
    print(f"Fetching {NUM_MEETINGS} meetings for {CONGRESS} {CHAMBER}...")
    meetings = get_meetings(congress=CONGRESS, chamber=CHAMBER, limit=NUM_MEETINGS)
    
    print(f"Found {len(meetings)} meetings. Starting transcript extraction...")
    texts, closed_count, unknown_count, unknown_titles = extract_and_process_meetings(meetings, NUM_MEETINGS)

    output_path = f"./ragExperiment/committee_meetings_{CONGRESS}_{CHAMBER}_{NUM_MEETINGS}.json"
    save_transcripts(texts, output_path)

    analyze_token_count(output_path)

    print("\n--- Analysis Summary ---")
    print(f"Successfully processed: {len(texts)}")
    print(f"Closed meetings (no transcript): {closed_count}")
    print(f"Meetings with other errors: {unknown_count}")
    if unknown_titles:
        print("Titles of meetings with errors:")
        for title in unknown_titles:
            print(f"  - {title}")

def getNumMeetings(file_path):
    """
    Given a file with structure {congress: {chamber: {eventid: text, ...}, ...}, ...},
    returns the total number of events/meetings in the file.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    total_events = 0
    for congress in data.values():
        for chamber in congress.values():
            total_events += len(chamber)
    return total_events
def getNumTokens(file_path):
    """
    Given a file with structure {congress: {chamber: {eventid: text, ...}, ...}, ...},
    returns the total number of tokens in all meeting texts.
    Uses tiktoken if available, otherwise falls back to word count.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    all_text = []
    for congress in data.values():
        for chamber in congress.values():
            for text in chamber.values():
                all_text.append(text)
    joined_text = "\n".join(all_text)
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(joined_text))
    except ImportError:
        # Fallback: count words as a rough proxy
        return len(joined_text.split())


if __name__ == "__main__":
    print(getNumMeetings(f"./ragExperiment/committee_meetings_{CONGRESS}_{CHAMBER}_{NUM_MEETINGS}.json"))
    print(getNumTokens(f"./ragExperiment/committee_meetings_{CONGRESS}_{CHAMBER}_{NUM_MEETINGS}.json"))