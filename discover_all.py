"""
Discovers ALL article pages on hexer.fandom.com with their primary category.
Saves results to all_pages_discovered.csv.
"""
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path

BASE_URL = "https://hexer.fandom.com/api.php"

# Keywords that mark categories unsuitable as folder names
SKIP_CAT_KEYWORDS = ["Bilder", "Vorlagen", "Vorlage", "Hilfe"]

session = requests.Session()
session.headers.update({"User-Agent": "WikiBot/1.0 (hexer.fandom.com)"})


def pick_category(categories: list[str]) -> str:
    for cat in categories:
        if not any(kw in cat for kw in SKIP_CAT_KEYWORDS):
            return cat
    return "Sonstige"


def discover_all_pages() -> list[dict]:
    params = {
        "action": "query",
        "generator": "allpages",
        "gaplimit": 50,
        "gapnamespace": 0,
        "gapfilterredir": "nonredirects",
        "prop": "categories",
        "cllimit": "max",
        "clshow": "!hidden",
        "format": "json",
        "formatversion": "2",
    }
    pages = []
    with tqdm(desc="Seiten entdecken", unit="Seite") as pbar:
        while True:
            r = session.get(BASE_URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            for page in data["query"]["pages"]:
                title = page["title"]
                cats = [c["title"].replace("Kategorie:", "") for c in page.get("categories", [])]
                endpoint = title.replace(" ", "_")
                pages.append({
                    "Ort": title,
                    "endpunkt": endpoint,
                    "url": f"https://hexer.fandom.com/wiki/{endpoint}",
                    "kategorie": pick_category(cats),
                })
            pbar.update(len(data["query"]["pages"]))
            cont = data.get("continue", {})
            if not cont:
                break
            params.update(cont)
    return pages


if __name__ == "__main__":
    print("Entdecke alle Seiten auf hexer.fandom.com ...")
    pages = discover_all_pages()

    df = pd.DataFrame(pages, columns=["Ort", "endpunkt", "url", "kategorie"])
    df.sort_values(["kategorie", "Ort"], inplace=True)

    output = Path("all_pages_discovered.csv")
    df.to_csv(output, index=False, encoding="utf-8")

    print(f"\n{len(df)} Seiten in {df['kategorie'].nunique()} Kategorien")
    print("\nTop-20 Kategorien:")
    print(df["kategorie"].value_counts().head(20).to_string())
    print(f"\nGespeichert in: {output}")
