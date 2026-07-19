"""
Fetches content for ALL discovered wiki pages (from all_pages_discovered.csv)
and saves each as wiki/{kategorie}/{endpunkt}.md.

Uses batched API calls (50 titles per request) for speed.
Skips files that already exist anywhere under wiki/ (resumable).
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
BATCH_SIZE = 50
MAX_WORKERS = 4

session = requests.Session()
session.headers.update({"User-Agent": "WikiBot/1.0 (hexer.fandom.com)"})


def safe_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def build_existing_index(base: Path) -> set[str]:
    """Collect stems of all .md files already saved under wiki/."""
    return {f.stem for f in base.rglob("*.md")}


def fetch_batch(rows: list[dict], existing: set[str]) -> list[tuple[str, str]]:
    """
    Fetch content for up to BATCH_SIZE pages in a single API call.
    Returns list of (status, title) tuples.
    """
    to_fetch = [r for r in rows if safe_name(r["endpunkt"]) not in existing]
    skipped = [("skipped", r["Ort"]) for r in rows if safe_name(r["endpunkt"]) in existing]

    if not to_fetch:
        return skipped

    titles = "|".join(r["Ort"] for r in to_fetch)
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": titles,
        "rvprop": "content",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json",
    }

    # Build lookup: title → row metadata
    meta = {r["Ort"]: r for r in to_fetch}

    for attempt in range(6):
        try:
            r = session.get(BASE_URL, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            data = r.json()
            results = []
            for page in data["query"]["pages"]:
                title = page["title"]
                row = meta.get(title)
                if row is None:
                    continue
                kategorie = row.get("kategorie", "Sonstige")
                endpoint = row["endpunkt"]
                folder = OUTPUT_DIR / safe_name(kategorie)
                folder.mkdir(parents=True, exist_ok=True)
                filepath = folder / f"{safe_name(endpoint)}.md"

                if "revisions" not in page:
                    content = f"# {title}\n\n*(Kein Inhalt verfügbar)*\n"
                else:
                    content = page["revisions"][0]["slots"]["main"]["content"]

                filepath.write_text(content, encoding="utf-8")
                existing.add(safe_name(endpoint))
                results.append(("ok", title))

            return skipped + results

        except requests.HTTPError as e:
            if attempt < 5:
                time.sleep(2 ** attempt)
            else:
                return skipped + [("error", f"{r['Ort']}: HTTP error") for r in to_fetch]
        except Exception as e:
            return skipped + [("error", f"Batch error: {e}")]

    return skipped + [("error", f"max retries: batch of {len(to_fetch)}")]


if __name__ == "__main__":
    input_csv = Path("all_pages_discovered.csv")
    if not input_csv.exists():
        print("all_pages_discovered.csv nicht gefunden. Bitte zuerst discover_all.py ausführen.")
        raise SystemExit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(input_csv, encoding="utf-8")
    rows = df.to_dict("records")

    print(f"Lade bestehende Dateien aus wiki/ ...")
    existing = build_existing_index(OUTPUT_DIR)
    print(f"{len(existing)} bereits vorhanden, {len(rows) - len(existing)} noch zu laden\n")

    # Split into batches
    batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]

    ok = skipped = errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_batch, batch, existing): batch for batch in batches}
        with tqdm(total=len(rows), desc="Seiten abrufen", unit="Seite") as pbar:
            for future in as_completed(futures):
                results = future.result()
                for status, msg in results:
                    if status == "ok":
                        ok += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        errors += 1
                        tqdm.write(f"FEHLER: {msg}")
                pbar.update(len(results))

    print(f"\nFertig: {ok} gespeichert, {skipped} übersprungen, {errors} Fehler")
    print(f"Dateien in: {OUTPUT_DIR.resolve()}")
    print()
    print("Ordnerstruktur:")
    for sub in sorted(OUTPUT_DIR.iterdir()):
        if sub.is_dir():
            count = sum(1 for f in sub.iterdir() if f.suffix == ".md")
            print(f"  wiki/{sub.name}/ — {count} Dateien")
