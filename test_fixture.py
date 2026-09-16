"""Offline check of the parsing logic against Wikipedia-shaped markup."""
from bs4 import BeautifulSoup
import pandas as pd

import falcon9_webscraping as f9

HTML = """
<html><body>
<table class="wikitable plainrowheaders">
<tr>
 <th scope="col">Flight No.</th>
 <th scope="col">Date and<br />time (<a href="/wiki/UTC">UTC</a>)</th>
 <th scope="col"><a href="/wiki/Falcon_9">Version,<br />booster</a> <sup class="reference">[b]</sup></th>
 <th scope="col">Launch site</th>
 <th scope="col">Payload<sup class="reference">[c]</sup></th>
 <th scope="col">Payload mass</th>
 <th scope="col">Orbit</th>
 <th scope="col">Customer</th>
 <th scope="col">Launch<br />outcome</th>
 <th scope="col"><a href="/wiki/landing">Booster<br />landing</a></th>
</tr>
<tr>
 <th scope="row" rowspan="2">1</th>
 <td rowspan="2">4 June 2010,<br />18:45</td>
 <td rowspan="2">F9 v1.0<sup class="reference">[7]</sup><br />B0003.1<sup class="reference">[8]</sup></td>
 <td rowspan="2"><a href="/wiki/CCAFS">CCAFS</a>, <a href="/wiki/SLC-40">SLC&#160;40</a></td>
 <td>Dragon Spacecraft Qualification Unit</td>
 <td rowspan="2"><abbr title="unknown">&#160;</abbr></td>
 <td><a href="/wiki/LEO">LEO</a></td>
 <td><a href="/wiki/SpaceX">SpaceX</a></td>
 <td class="table-success">Success</td>
 <td class="table-failure">Failure<sup class="reference">[9]</sup><br /><small>(parachute)</small></td>
</tr>
<tr><td colspan="9">First flight of Falcon 9 v1.0. Reached orbit with a dummy payload.</td></tr>
<tr>
 <th scope="row" rowspan="2">20</th>
 <td rowspan="2">22 December 2015,<br />01:29</td>
 <td rowspan="2">F9 FT<br />B1019</td>
 <td rowspan="2"><a href="/wiki/CCAFS">CCAFS</a>, <a href="/wiki/SLC-40">SLC&#160;40</a></td>
 <td>Orbcomm-OG2 (11 satellites)</td>
 <td rowspan="2">2,034&#160;kg (4,484&#160;lb)</td>
 <td><a href="/wiki/LEO">LEO</a></td>
 <td>Orbcomm</td>
 <td class="table-success">Success</td>
 <td class="table-success">Success<br /><small>(ground pad)</small></td>
</tr>
<tr><td colspan="9">First successful landing of an orbital-class booster.</td></tr>
</table>
</body></html>
"""

soup = BeautifulSoup(HTML, "html.parser")

tables = f9.find_launch_tables(soup)
assert len(tables) == 1, tables
print("Column names:", f9.column_names(tables[0]))

records = []
f9.parse_table(tables[0], records)
df = pd.DataFrame(records)
df["FlightNumber"] = pd.to_numeric(df["FlightNumber"])
df["Date"] = pd.to_datetime(df["Date"], format="mixed")

print()
print(df.to_string())
print()
print(df.dtypes)

assert list(df.FlightNumber) == [1, 20]
assert list(df.BoosterSerial) == ["B0003.1", "B1019"]
assert list(df.BoosterVersion) == ["F9 v1.0", "F9 FT"]
assert list(df.Time) == ["18:45", "01:29"]
assert list(df.PayloadMass) == ["", "2034 kg"]
assert df.LaunchSite.iloc[0] == "CCAFS, SLC 40"
assert df.BoosterLanding.iloc[0] == "Failure (parachute)"
assert df.BoosterLanding.iloc[1] == "Success (ground pad)"
print("\nAll assertions passed.")
