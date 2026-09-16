"""
Static, tile-free fallback for spacex_sites_map.html.

This sandbox has no outbound network access, so it can neither install
folium nor download OpenStreetMap tiles to render a real screenshot of the
interactive map. This script draws the same geometry (sites, per-launch
outcomes, coastline points, connecting lines) as a plain matplotlib
scatter plot with axis = degrees latitude/longitude, so you can sanity-check
the coordinates and layout before running spacex_folium_map.py locally to
get the real interactive version.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

spacex_df = pd.read_csv("spacex_launch_geo.csv")
sites = spacex_df.groupby("LaunchSite", as_index=False).agg(Lat=("Lat", "first"), Long=("Long", "first"))

# Every launch from one site shares the exact same pad coordinate, so plotting
# them as-is would draw one dot per site. Add a small random jitter (visual
# only, not a real coordinate) so the mix of outcomes at each site is visible.
import numpy as np
rng = np.random.default_rng(0)
spacex_df["LatJitter"] = spacex_df["Lat"] + rng.normal(0, 0.006, len(spacex_df))
spacex_df["LongJitter"] = spacex_df["Long"] + rng.normal(0, 0.006, len(spacex_df))

COASTLINE_POINTS = {
    "CCAFS SLC-40": (28.56367, -80.56822),
    "KSC LC-39A":   (28.60828, -80.58803),
    "VAFB SLC-4E":  (34.63296, -120.62480),
}

fig, axes = plt.subplots(1, 2, figsize=(13, 6))

# East coast panel: CCAFS + KSC sit ~4 km apart
east = spacex_df[spacex_df["LaunchSite"].isin(["CCAFS SLC-40", "KSC LC-39A"])]
ax = axes[0]
for cls, color, label in [(1, "green", "Success"), (0, "red", "Failure/no attempt")]:
    subset = east[east["class"] == cls]
    ax.scatter(subset["LongJitter"], subset["LatJitter"], c=color, s=60, alpha=0.7,
               edgecolor="black", linewidth=0.5, label=label)
for site_name in ["CCAFS SLC-40", "KSC LC-39A"]:
    lat, lon = sites.set_index("LaunchSite").loc[site_name, ["Lat", "Long"]]
    clat, clon = COASTLINE_POINTS[site_name]
    ax.plot([lon, clon], [lat, clat], "b--", linewidth=1)
    ax.scatter([clon], [clat], marker="x", c="blue", s=80)
    ax.annotate(site_name, (lon, lat), textcoords="offset points", xytext=(6, 6), fontsize=8)
ax.set_title("Cape Canaveral / Kennedy (Florida)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend(fontsize=8)

# West coast panel: VAFB
west = spacex_df[spacex_df["LaunchSite"] == "VAFB SLC-4E"]
ax = axes[1]
for cls, color, label in [(1, "green", "Success"), (0, "red", "Failure/no attempt")]:
    subset = west[west["class"] == cls]
    ax.scatter(subset["LongJitter"], subset["LatJitter"], c=color, s=60, alpha=0.7,
               edgecolor="black", linewidth=0.5, label=label)
lat, lon = sites.set_index("LaunchSite").loc["VAFB SLC-4E", ["Lat", "Long"]]
clat, clon = COASTLINE_POINTS["VAFB SLC-4E"]
ax.plot([lon, clon], [lat, clat], "b--", linewidth=1)
ax.scatter([clon], [clat], marker="x", c="blue", s=80)
ax.annotate("VAFB SLC-4E", (lon, lat), textcoords="offset points", xytext=(6, 6), fontsize=8)
ax.set_title("Vandenberg (California)")
ax.set_xlabel("Longitude")
ax.legend(fontsize=8)

fig.suptitle("Launch sites, per-launch landing outcome, and nearest coastline point\n"
             "(plain lat/lon scatter — no basemap tiles; real map is spacex_sites_map.html)")
fig.tight_layout()
fig.savefig("spacex_sites_static_fallback.png", dpi=130, bbox_inches="tight")
print("Saved spacex_sites_static_fallback.png")
