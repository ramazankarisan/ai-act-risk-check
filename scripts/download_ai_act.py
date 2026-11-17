"""Download the English text of the EU AI Act (Regulation (EU) 2024/1689) once.

EUR-Lex's HTML page sits behind a bot-protection challenge, so the file is fetched from the
Publications Office CELLAR service, the official machine-readable source for the same
document. Citations still point to the human-readable EUR-Lex page (`EURLEX_URL`).
"""

from pathlib import Path

import httpx2

CELEX_ID = "32024R1689"
CELLAR_URL = f"http://publications.europa.eu/resource/celex/{CELEX_ID}"
EURLEX_URL = f"https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{CELEX_ID}"
TARGET_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "ai_act_en.html"
TIMEOUT_SECONDS = 60.0
EXPECTED_MARKER = "Article\u00a05".encode()  # EUR-Lex uses a non-breaking space


def fetch_html(url: str = CELLAR_URL) -> bytes:
    """Fetch the English XHTML of the act via CELLAR content negotiation.

    Raises `ValueError` if the response is not a complete document, e.g. an empty body.
    """
    response = httpx2.get(
        url,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={
            "Accept": "application/xhtml+xml, text/html",
            "Accept-Language": "eng",
            "User-Agent": "ai-act-risk-check corpus downloader",
        },
    )
    response.raise_for_status()
    if response.status_code != 200 or EXPECTED_MARKER not in response.content:
        raise ValueError(
            f"Unexpected response from {response.url}: status {response.status_code}, "
            f"{len(response.content)} bytes, marker {EXPECTED_MARKER!r} missing"
        )
    return response.content


def download(target: Path = TARGET_PATH) -> Path:
    """Save the act's HTML to `target`, skipping the download if the file already exists.

    Returns the path of the (existing or newly written) file.
    """
    if target.exists():
        print(f"Already downloaded, skipping: {target}")
        return target

    content = fetch_html()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    print(f"Saved {len(content):,} bytes to {target}")
    return target


if __name__ == "__main__":
    download()
