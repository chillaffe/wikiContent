import pandas as pd
import requests
from tqdm import tqdm
from pathlib import Path
from bs4 import BeautifulSoup

input_file = Path("Scripte/HardCode/4674e7b4.csv")
output_file = Path("Scripte/HardCode/4674e7b4_mit_htmltext.csv")

tqdm.pandas(desc="DataFrame Operation")
df = pd.read_csv(input_file.resolve())

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

def fetch_html_text(url):
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text(" ", strip=True)
    except Exception as e:
        return f"ERROR: {e}"

#df["htmlText"] = [fetch_html_text(url) for url in df["url"]]
df['htmlText'] = df.progress_apply(lambda htmltext:fetch_html_text(df['url']))

df.to_csv(output_file.resolve(), index=False, encoding="utf-8-sig")

print(f"Gespeichert: {output_file.name}")