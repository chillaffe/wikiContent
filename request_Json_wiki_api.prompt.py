import requests
from tqdm import tqdm
import pandas as pd
from pathlib import Path

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "WikiContentBot/1.0 (hexer.fandom.com scraper)"})


def fetch_wiki_content(title):
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json",
    }
    try:
        r = SESSION.get("https://hexer.fandom.com/api.php", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        content = str(data["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"])
        return {"Endpunkt": title, "Response": content, "rawResponse": data}
    except Exception as e:
        return {"Endpunkt": title, "Response": f"Error: {str(e)}"}


# Prefer the auto-discovered list; fall back to the legacy CSV
discovered = Path("locations_discovered.csv")
legacy = Path("witcher_orte_493.csv")
inputfile = discovered if discovered.exists() else legacy
print(f"Eingabedatei: {inputfile}")

input_df = pd.read_csv(inputfile.resolve(), encoding="utf-8", header=0)

# API ABRUF MIT MAP
results = list(tqdm(map(fetch_wiki_content, input_df["endpunkt"]), total=len(input_df)))

# OUTPUT CSV SPEICHERN
output_df = pd.DataFrame(results)
output_df.to_csv("wiki_contents.csv", index=None, encoding="utf-8")
print(f"CSV gespeichert als wiki_contents.csv ({len(output_df)} Einträge)")