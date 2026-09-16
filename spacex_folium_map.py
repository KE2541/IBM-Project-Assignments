"""
Interactive Folium visual analytics for Falcon 9 launch sites.

Reads spacex_launch_geo.csv (built by build_spacex_geo.py) and produces
spacex_sites_map.html — an interactive map with:
  - a Circle + text-label Marker on each launch site
  - a MarkerCluster of every individual launch, colour-coded green/red
    by landing outcome
  - a MousePosition readout for picking a coastline point by eye
  - a PolyLine + distance label from each site to its nearest coastline

Requirements: folium, pandas
    pip install folium pandas

This script only builds the HTML file; it does not attempt a screenshot.
Rendering a PNG requires a headless browser (selenium + chromedriver) that
can reach the internet to fetch OpenStreetMap tiles — do that locally with:

    from selenium import webdriver
    driver = webdriver.Chrome()
    driver.set_window_size(1200, 900)
    driver.get("file://" + os.path.abspath("spacex_sites_map.html"))
    time.sleep(2)  # let tiles load
    driver.save_screenshot("spacex_sites_map.png")
    driver.quit()
"""

import math

import folium
import pandas as pd
from folium.features import DivIcon
from folium.plugins import MarkerCluster, MousePosition

# ----------------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------------
spacex_df = pd.read_csv("spacex_launch_geo.csv")

launch_sites_df = (
    spacex_df.groupby("LaunchSite", as_index=False)
    .agg(Lat=("Lat", "first"), Long=("Long", "first"))
)

# Manually-picked nearest-coastline point for each site (verify/adjust these
# by eye on the rendered map using the MousePosition readout in the corner).
COASTLINE_POINTS = {
    "CCAFS SLC-40": (28.56367, -80.56822),
    "KSC LC-39A":   (28.60828, -80.58803),
    "VAFB SLC-4E":  (34.63296, -120.62480),
}


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    R = 6373.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ----------------------------------------------------------------------------
# Base map, centred on the continental US launch corridor
# ----------------------------------------------------------------------------
site_map = folium.Map(location=[29.5, -95], zoom_start=4.5)

# ----------------------------------------------------------------------------
# Task 1 & 2: mark every launch site with a Circle + text-label Marker
# ----------------------------------------------------------------------------
for _, row in launch_sites_df.iterrows():
    coord = [row["Lat"], row["Long"]]

    folium.Circle(
        coord,
        radius=1000,
        color="#d35400",
        fill=True,
        fill_opacity=0.6,
    ).add_child(folium.Popup(row["LaunchSite"])).add_to(site_map)

    folium.Marker(
        coord,
        icon=DivIcon(
            icon_size=(150, 36),
            icon_anchor=(0, 0),
            html=f'<div style="font-size:12px;color:#d35400;font-weight:bold">{row["LaunchSite"]}</div>',
        ),
    ).add_to(site_map)

# ----------------------------------------------------------------------------
# Task 3: marker_color column, and one Marker per launch in a MarkerCluster
# ----------------------------------------------------------------------------
spacex_df["marker_color"] = spacex_df["class"].apply(lambda c: "green" if c == 1 else "red")

marker_cluster = MarkerCluster().add_to(site_map)

for _, row in spacex_df.iterrows():
    folium.Marker(
        [row["Lat"], row["Long"]],
        icon=folium.Icon(color="white", icon_color=row["marker_color"]),
        popup=(
            f"Flight {row['FlightNumber']} — {row['LaunchSite']}<br>"
            f"{row['Payload']}<br>"
            f"Landing: {row['LandingOutcome']}"
        ),
    ).add_to(marker_cluster)

# ----------------------------------------------------------------------------
# MousePosition, for picking a coastline point by hand on the rendered map
# ----------------------------------------------------------------------------
MousePosition(
    position="topright",
    separator=" | Long: ",
    prefix="Lat: ",
    num_digits=5,
).add_to(site_map)

# ----------------------------------------------------------------------------
# Task 4: coastline point + PolyLine + distance label for each site
# ----------------------------------------------------------------------------
for site_name, (site_lat, site_lon) in zip(launch_sites_df["LaunchSite"],
                                            zip(launch_sites_df["Lat"], launch_sites_df["Long"])):
    coast_lat, coast_lon = COASTLINE_POINTS[site_name]
    distance_km = haversine(site_lat, site_lon, coast_lat, coast_lon)

    folium.Marker(
        [coast_lat, coast_lon],
        icon=DivIcon(
            icon_size=(200, 36),
            icon_anchor=(0, 0),
            html=f'<div style="font-size:11px;color:#2874a6;font-weight:bold">{distance_km:.2f} km</div>',
        ),
    ).add_to(site_map)

    folium.PolyLine(
        locations=[[site_lat, site_lon], [coast_lat, coast_lon]],
        weight=2,
        color="#2874a6",
    ).add_to(site_map)

    print(f"{site_name}: {distance_km:.2f} km to nearest coastline point")

# ----------------------------------------------------------------------------
# Save
# ----------------------------------------------------------------------------
site_map.save("spacex_sites_map.html")
print("\nSaved spacex_sites_map.html")
