"""
Discovers all location pages from hexer.fandom.com by recursively traversing
the 'Kategorie:Orte' category tree via the MediaWiki API.
Saves results to locations_discovered.csv for use by request_Json_wiki_api.prompt.py.
"""
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path

BASE_URL = "https://hexer.fandom.com/api.php"
ROOT_CATEGORY = "Kategorie:Orte"

# Subcategories that lead to non-location content (characters, races, magic, culture).
# "Bilder" image-gallery categories are also skipped via name check below.
SKIP_CATEGORIES = {
    # Creatures / character types
    "Rassen", "Elfen", "Vampire", "Hexer", "Menschen", "Dryaden", "Drachen",
    "Gnome", "Halbelfen", "Halblinge", "Trolle", "Viertelelfen", "Vran (Rasse)", "Zwerge",
    # Magic / skills
    "Magie", "The Witcher Magie",
    # Military
    "Streitkräfte", "Militärische Einheiten", "Militärische Ränge",
    # Culture / history (no location pages)
    "Geschichte", "Almanach", "Folklore", "Sprachen", "Symbole",
    "Gewichte und Maße", "Bilder - Heraldik", "Gottheiten", "Währungen",
    # Nationalities / peoples (character pages, not locations)
    "Aedirner", "Caingorner", "Cintrier", "Lyrier und Rivier", "Mahakamer",
    "Nilfgaarder", "Ophiri", "Redanier", "Skelliger", "Temerier", "Toussainter",
    "Kaedwener", "Keracker", "Kovirer",
    # Other non-location people categories
    "Familien", "Herrscher", "Priester", "Gelehrte", "Zauberer",
}

session = requests.Session()
session.headers.update({"User-Agent": "WikiLocationBot/1.0 (hexer.fandom.com scraper)"})


def _should_follow(category_title: str) -> bool:
    """Return False for known non-location category families."""
    name = category_title.replace("Kategorie:", "")
    if name in SKIP_CATEGORIES:
        return False
    # Skip pure image / media galleries
    if "Bilder" in name and "Orte" not in name and "Karten" not in name:
        return False
    return True


def get_category_members(category: str):
    """Yield all members (pages + subcategories) of a category, handling pagination."""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": 500,
        "cmtype": "page|subcat",
        "format": "json",
        "formatversion": "2",
    }
    while True:
        r = session.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        yield from data["query"]["categorymembers"]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont


def discover_all_locations(root_category: str) -> list[dict]:
    """BFS over the location category tree; collect all article pages (namespace 0).
    Tracks the immediate category each page was first found in."""
    visited_categories: set[str] = set()
    pages: dict[str, dict] = {}
    queue = [root_category]

    with tqdm(desc="Kategorien", unit="cat") as cat_bar:
        while queue:
            category = queue.pop(0)
            if category in visited_categories:
                continue
            visited_categories.add(category)
            cat_bar.set_postfix_str(category.replace("Kategorie:", ""))
            cat_bar.update(1)

            for member in get_category_members(category):
                ns, title = member["ns"], member["title"]
                if ns == 0:  # article namespace — first discovery wins
                    endpoint = title.replace(" ", "_")
                    if title not in pages:
                        pages[title] = {
                            "Ort": title,
                            "endpunkt": endpoint,
                            "url": f"https://hexer.fandom.com/wiki/{endpoint}",
                            "kategorie": category.replace("Kategorie:", ""),
                        }
                elif ns == 14:  # subcategory namespace
                    if title not in visited_categories and _should_follow(title):
                        queue.append(title)

    return list(pages.values())


if __name__ == "__main__":
    print(f"Starte Suche ab '{ROOT_CATEGORY}' ...")
    locations = discover_all_locations(ROOT_CATEGORY)

    output_path = Path("locations_discovered.csv")
    df = pd.DataFrame(locations, columns=["Ort", "endpunkt", "url", "kategorie"])
    df.sort_values("Ort", inplace=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"\n{len(df)} Orte gefunden und gespeichert in '{output_path}'")
