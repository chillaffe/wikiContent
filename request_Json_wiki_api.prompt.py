import requests
from tqdm import tqdm
import pandas as pd
from pathlib import Path

def fetch_wiki_content(title):
    url = "https://hexer.fandom.com/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        #Nur ein Request per Endpunkt
        content = str(data['query']['pages'][0]['revisions'][0]['slots']['main']['content'])

        return {"Endpunkt": title, "Response": content, "rawResponse": data }
    except Exception as e:
        return {"Endpunkt": title, "Response": f"Error: {str(e)}"}

# INPUT CSV LADEN (Spalte "url" mit Titeln)
inputfile = Path("witcher_orte_493.csv")
input_df = pd.read_csv(inputfile.resolve(), encoding="utf-8",header=0)  # Erstelle diese CSV mit Spalte "url"

# API ABRUF MIT MAP
results = list(tqdm(map(fetch_wiki_content, input_df["endpunkt"]),total=input_df.__len__()))

# OUTPUT CSV SPEICHERN
output_df = pd.DataFrame(results)

output_df.to_csv("wiki_contents.csv", index=None, encoding="utf-8")
print("CSV gespeichert als wiki_contents.csv")