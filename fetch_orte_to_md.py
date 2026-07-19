"""
Fetches wiki content for each discovered location and saves it as a .md file
under wiki/{kategorie}/{endpunkt}.md. Skips existing files (resumable).
Rate-limited with retry/backoff to avoid 429 errors.
"""
import re
import time
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://hexer.fandom.com/api.php"
OUTPUT_DIR = Path("wiki")
MAX_WORKERS = 3

session = requests.Session()
session.headers.update({"User-Agent": "WikiContentBot/1.0 (hexer.fandom.com scraper)"})


def safe_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def fetch_and_save(row: dict) -> tuple[str, str]:
    title = row["Ort"]
    endpoint = row["endpunkt"]
    kategorie = row.get("kategorie", "Sonstige")

    folder = OUTPUT_DIR / safe_name(kategorie)
    folder.mkdir(parents=True, exist_ok=True)
    filepath = folder / f"{safe_name(endpoint)}.md"

    if filepath.exists():
        return "skipped", title

    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json",
    }

    for attempt in range(6):
        try:
            r = session.get(BASE_URL, params=params, timeout=20)
            if r.status_code == 429:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            page = data["query"]["pages"][0]
            if "revisions" not in page:
                content = f"# {title}\n\n*(Kein Inhalt verfügbar)*\n"
            else:
                content = page["revisions"][0]["slots"]["main"]["content"]
            filepath.write_text(content, encoding="utf-8")
            return "ok", title
        except requests.HTTPError as e:
            if attempt < 5:
                time.sleep(2 ** attempt)
            else:
                return "error", f"{title}: {e}"
        except Exception as e:
            return "error", f"{title}: {e}"

    return "error", f"{title}: max retries exceeded"


if __name__ == "__main__":
    input_csv = Path("locations_discovered.csv")
    if not input_csv.exists():
        print("locations_discovered.csv nicht gefunden. Bitte zuerst discover_locations.py ausführen.")
        raise SystemExit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    rows = pd.read_csv(input_csv, encoding="utf-8").to_dict("records")

    ok = skipped = errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_and_save, row): row for row in rows}
        with tqdm(total=len(rows), desc="Orte abrufen", unit="Ort") as pbar:
            for future in as_completed(futures):
                status, msg = future.result()
                if status == "ok":
                    ok += 1
                elif status == "skipped":
                    skipped += 1
                else:
                    errors += 1
                    tqdm.write(f"FEHLER: {msg}")
                pbar.update(1)

    print(f"\nFertig: {ok} gespeichert, {skipped} übersprungen, {errors} Fehler")
    print(f"Dateien in: {OUTPUT_DIR.resolve()}")
    print()
    print("Ordnerstruktur:")
    for sub in sorted(OUTPUT_DIR.iterdir()):
        if sub.is_dir():
            count = sum(1 for f in sub.iterdir() if f.suffix == ".md")
            print(f"  wiki/{sub.name}/ — {count} Dateien")
