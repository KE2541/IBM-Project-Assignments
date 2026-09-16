"""
Falcon 9 / Falcon Heavy launch records — web scraping with BeautifulSoup.

Source page:
    https://en.wikipedia.org/wiki/List_of_Falcon_9_and_Falcon_Heavy_launches

Output:
    spacex_web_scraped.csv  (one row per launch)

Requirements: requests, beautifulsoup4, pandas, lxml (optional, faster parser)
"""

import re
import sys
import unicodedata

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Live page. Wikipedia edits this constantly, so if you need a reproducible
# result, swap in a frozen revision instead, e.g.:
# STATIC_URL = ("https://en.wikipedia.org/w/index.php?title="
#               "List_of_Falcon_9_and_Falcon_Heavy_launches&oldid=1027686922")
URL = "https://en.wikipedia.org/wiki/List_of_Falcon_9_and_Falcon_Heavy_launches"

HEADERS = {"User-Agent": "falcon9-scraper/1.0 (educational data-science exercise)"}


# ----------------------------------------------------------------------------
# 1. Request the page and hand it to BeautifulSoup
# ----------------------------------------------------------------------------
def fetch_soup(url=URL):
    """GET the page and return a BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")


# ----------------------------------------------------------------------------
# 2. Helper functions to clean individual cells
# ----------------------------------------------------------------------------
def clean(text):
    """Normalise unicode, strip footnote markers and collapse whitespace."""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\[[^\]]*\]", "", text)          # [1], [note 2], ...
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:)])", r"\1", text)     # 'CCAFS , SLC 40' -> 'CCAFS, SLC 40'
    text = re.sub(r"\(\s+", "(", text)
    return text.strip()


def extract_column_from_header(th):
    """
    Turn a <th> header cell into a plain column name, or None if unusable.

    Footnote <sup> markers are removed outright; <br> becomes a space. Anchor
    text is kept, because headers like 'Version, Booster' and 'Booster landing'
    sit entirely inside a link.
    """
    th = BeautifulSoup(str(th), "html.parser")
    for tag in th.find_all("sup"):
        tag.extract()
    name = clean(th.get_text(" "))
    if not name or name.isdigit():
        return None
    return name


def date_time(cell):
    """Split a date/time cell into ('4 June 2010', '18:45')."""
    text = clean(cell.get_text(" "))
    match = re.match(r"(\d{1,2}\s+\w+\s+\d{4})[,\s]*(\d{1,2}:\d{2})?", text)
    if match:
        return match.group(1), (match.group(2) or "")
    return text, ""


def booster_version(cell):
    """'F9 v1.0B0003.1' -> version 'F9 v1.0', booster 'B0003.1'."""
    text = clean(cell.get_text(" "))
    match = re.search(r"(B\d{4}\.?\d*)", text)
    if match:
        return clean(text[: match.start()]), match.group(1)
    return text, ""


def get_mass(cell):
    """Pull the kilogram figure out of a payload-mass cell -> '3170 kg'."""
    text = clean(cell.get_text(" "))
    match = re.search(r"([\d,\.]+)\s*kg", text)
    if match:
        return f"{match.group(1).replace(',', '')} kg"
    return ""


def landing_status(cell):
    """Landing / launch outcome, e.g. 'Success (ground pad)'."""
    return clean(cell.get_text(" "))


# ----------------------------------------------------------------------------
# 3. Locate the launch tables and read the column names
# ----------------------------------------------------------------------------
def find_launch_tables(soup):
    """
    The article splits launches across several 'wikitable' tables (one per
    year / vehicle). Keep only the ones whose header row starts with the
    flight-number column.
    """
    tables = []
    for table in soup.find_all("table", class_="wikitable"):
        header = table.find("tr")
        if header is None:
            continue
        head_text = clean(header.get_text(" ")).lower()
        if "flight no" in head_text and "launch site" in head_text:
            tables.append(table)
    return tables


def column_names(table):
    """Extract usable column names from a table's header row."""
    names = []
    for th in table.find("tr").find_all("th"):
        name = extract_column_from_header(th)
        if name is not None:
            names.append(name)
    return names


# ----------------------------------------------------------------------------
# 4. Walk the rows and build the records
# ----------------------------------------------------------------------------
def is_launch_row(row):
    """
    A launch row starts with a <th scope="row"> holding the flight number.
    The row directly after it is the free-text mission description, which we
    skip, and so are the section sub-headers.
    """
    first = row.find(["th", "td"])
    if first is None:
        return False
    text = clean(first.get_text())
    return bool(re.fullmatch(r"\d+\.?", text))


def parse_table(table, records):
    """Append every launch in `table` to the `records` list."""
    for row in table.find_all("tr"):
        if not is_launch_row(row):
            continue

        cells = row.find_all(["th", "td"])
        if len(cells) < 8:          # malformed / continuation row
            continue

        flight_number = clean(cells[0].get_text()).rstrip(".")
        date, time = date_time(cells[1])
        version, booster = booster_version(cells[2])

        records.append(
            {
                "FlightNumber": flight_number,
                "Date": date,
                "Time": time,
                "BoosterVersion": version,
                "BoosterSerial": booster,
                "LaunchSite": clean(cells[3].get_text(" ")),
                "Payload": clean(cells[4].get_text(" ")),
                "PayloadMass": get_mass(cells[5]),
                "Orbit": clean(cells[6].get_text(" ")),
                "Customer": clean(cells[7].get_text(" ")),
                "LaunchOutcome": landing_status(cells[8]) if len(cells) > 8 else "",
                "BoosterLanding": landing_status(cells[9]) if len(cells) > 9 else "",
            }
        )


# ----------------------------------------------------------------------------
# 5. Put it together
# ----------------------------------------------------------------------------
def scrape(url=URL):
    soup = fetch_soup(url)
    tables = find_launch_tables(soup)
    if not tables:
        raise RuntimeError("No launch tables found — the page layout may have changed.")

    print(f"Found {len(tables)} launch table(s).")
    print("Columns on the first table:", column_names(tables[0]))

    records = []
    for table in tables:
        parse_table(table, records)

    df = pd.DataFrame(records)
    df["FlightNumber"] = pd.to_numeric(df["FlightNumber"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce")
    df = df.dropna(subset=["FlightNumber"]).sort_values("FlightNumber")
    return df.reset_index(drop=True)


if __name__ == "__main__":
    try:
        launches = scrape()
    except requests.RequestException as exc:
        sys.exit(f"Could not download the page: {exc}")

    print(f"\n{len(launches)} launch records scraped.\n")
    print(launches.head(10).to_string())

    launches.to_csv("spacex_web_scraped.csv", index=False)
    print("\nSaved to spacex_web_scraped.csv")
