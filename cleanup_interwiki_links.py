"""
Durchlaeuft den Ordner wiki/ rekursiv und entfernt Interwiki-Sprachlinks
(z.B. "[[it:Luogo di Potere]]", "[[en:Place of Power]]", "[[pt-br:...]]")
aus allen .md Dateien. Eine Datei kann mehrere solcher Zeilen enthalten,
je eine pro Sprache.

Namespace-Links wie [[Kategorie:...]], [[Datei:...]] oder [[Bild:...]]
bleiben erhalten, da Sprachcodes in MediaWiki immer kleingeschrieben sind,
waehrend Namespaces grossgeschrieben werden.
"""
import re
from pathlib import Path

WIKI_DIR = Path("wiki")

# Ganze Zeile besteht nur aus einem Interwiki-Sprachlink, z.B. "[[it:Luogo di Potere]]"
INTERWIKI_LINE = re.compile(r"^\[\[[a-z]{2,3}(-[a-z0-9]+)*:[^\[\]]*\]\]\s*$")


def clean_content(text: str) -> tuple[str, int]:
    lines = text.splitlines()
    kept = [line for line in lines if not INTERWIKI_LINE.match(line.strip())]
    removed = len(lines) - len(kept)
    cleaned = "\n".join(kept)
    if text.endswith("\n"):
        cleaned += "\n"
    return cleaned, removed


def main() -> None:
    if not WIKI_DIR.exists():
        print(f"Ordner '{WIKI_DIR}' nicht gefunden.")
        raise SystemExit(1)

    md_files = sorted(WIKI_DIR.rglob("*.md"))
    changed_files = 0
    total_removed = 0

    for filepath in md_files:
        original = filepath.read_text(encoding="utf-8")
        cleaned, removed = clean_content(original)
        if removed:
            filepath.write_text(cleaned, encoding="utf-8")
            changed_files += 1
            total_removed += removed
            print(f"{filepath}: {removed} Zeile(n) entfernt")

    print()
    print(f"Fertig: {len(md_files)} Dateien geprueft, {changed_files} veraendert, "
          f"{total_removed} Interwiki-Zeilen insgesamt entfernt")


if __name__ == "__main__":
    main()
