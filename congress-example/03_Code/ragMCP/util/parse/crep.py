from util.parse.text_parse import __extract_text_from_html_url

# Extracts all the unique raw text URLs (.htm) that correspond to the endpoint where we can find the
# text of a committee report
def _parse_committee_report_text_links(text_items):

    seen_htm = set()
    parsed = []

    for item in text_items:

        url = (item.findtext('url') or '').strip()
        type = (item.findtext('type') or '').strip()
        is_errata = (item.findtext('isErrata') or '').strip().lower() in ('y', 'true')

        if url.endswith('.pdf'):
            continue

        elif url.endswith('.htm') or url.endswith('.html'):
            if url not in seen_htm:

                seen_htm.add(url)
                text = __extract_text_from_html_url(url)
                parsed.append({'url': url, 'type': type, 'isErrata': is_errata, 'text': text})

    return parsed