"""Download the English text of the EU AI Act (Regulation (EU) 2024/1689) once.

EUR-Lex's HTML page sits behind a bot-protection challenge, so the file is fetched from the
Publications Office CELLAR service, the official machine-readable source for the same
document. Chunks still cite the human-readable EUR-Lex page (`corpus.SOURCE_URL`).
"""

import hashlib
from pathlib import Path

import httpx2

from ai_act_check.corpus import CELEX_ID, RAW_HTML_PATH

CELLAR_URL = f"https://publications.europa.eu/resource/celex/{CELEX_ID}"
TIMEOUT_SECONDS = 60.0
EXPECTED_MARKER = "Article 5".encode()  # EUR-Lex uses a non-breaking space


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


def download(target: Path = RAW_HTML_PATH) -> Path:
    """Save the act's HTML to `target`, skipping the download if the file already exists.

    Returns the path of the (existing or newly written) file.
    """
    if target.exists():
        print(f"Already downloaded, skipping: {target}")
        return target

    content = fetch_html()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()
    print(f"Saved {len(content):,} bytes to {target} (sha256 {sha256})")
    return target


if __name__ == "__main__":
    download()
