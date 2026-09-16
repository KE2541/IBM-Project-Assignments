"""
Build spacex_launch_geo.csv: every launch record from "Spacex Data Set.db"
(SPACEXTABLE) plus each site's latitude/longitude and a binary landing
'class' column, ready for the Folium mapping script.

Site coordinates are the real published pad locations:
  CCAFS SLC-40  28.56230, -80.57735   Cape Canaveral SFS, FL
  KSC LC-39A    28.60809, -80.60397   Kennedy Space Center, FL
  VAFB SLC-4E   34.63209, -120.61084  Vandenberg SFB, CA

class = 1 if the first stage landed successfully (LandingOutcome starts
with 'Success'), else 0 — covers ground-pad and drone-ship successes as
positive, and every failure / no-attempt / precluded / controlled-descent
test as negative, consistent with the earlier EDA notebook.
"""

import sqlite3
import pandas as pd

SITE_COORDS = {
    "CCAFS SLC-40": (28.56230, -80.57735),
    "KSC LC-39A":   (28.60809, -80.60397),
    "VAFB SLC-4E":  (34.63209, -120.61084),
}

conn = sqlite3.connect("Spacex Data Set.db")
df = pd.read_sql_query("SELECT * FROM SPACEXTABLE ORDER BY FlightNumber;", conn)
conn.close()

df["Lat"] = df["LaunchSite"].map(lambda s: SITE_COORDS[s][0])
df["Long"] = df["LaunchSite"].map(lambda s: SITE_COORDS[s][1])
df["class"] = df["LandingOutcome"].str.startswith("Success").astype(int)

cols = ["FlightNumber", "Date", "BoosterVersion", "BoosterSerial", "LaunchSite",
        "Lat", "Long", "Payload", "PayloadMassKG", "Orbit", "Customer",
        "MissionOutcome", "LandingOutcome", "class"]
df = df[cols]

df.to_csv("spacex_launch_geo.csv", index=False)
print(f"Wrote spacex_launch_geo.csv: {len(df)} rows, {df['class'].sum()} successful landings")
print(df.groupby("LaunchSite")["class"].agg(["count", "sum", "mean"]))
