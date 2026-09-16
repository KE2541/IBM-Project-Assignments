"""
Falcon 9 first-stage landing — EDA and feature engineering.

Input:  spacex_web_scraped.csv  (produced by falcon9_webscraping.py)
Output: six figures as PNG + spacex_features.csv (model-ready, all float64)

Requirements: pandas, numpy, matplotlib, seaborn
"""

import re

import matplotlib
matplotlib.use("Agg")           # drop this line if you want interactive windows
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="deep")
PLOT_DIR = "."


# ----------------------------------------------------------------------------
# Load
# ----------------------------------------------------------------------------
df = pd.read_csv("spacex_web_scraped.csv")
print("Raw shape:", df.shape)


# ----------------------------------------------------------------------------
# Feature engineering
# ----------------------------------------------------------------------------
# Class: the prediction target. 1 = first stage recovered, 0 = not.
# 'No attempt' is a deliberate expendable flight, not a failed landing, so it
# gets dropped rather than labelled 0 — otherwise the model learns to predict
# heavy GTO payloads as "landing failures" when nobody ever tried to land them.
df["BoosterLanding"] = df["BoosterLanding"].fillna("")
attempted = ~df["BoosterLanding"].str.contains(
    "no attempt|not attempted|expended|ocean", case=False, na=False
)
df = df[attempted & df["BoosterLanding"].ne("")].copy()
df["Class"] = df["BoosterLanding"].str.startswith("Success").astype(int)

# LandingPad: the droneship or ground pad named in parentheses.
df["LandingPad"] = (
    df["BoosterLanding"].str.extract(r"\(([^)]+)\)", expand=False).fillna("Unknown")
)

# PayloadMass: strip the ' kg', coerce blanks to NaN, then fill with the mean.
df["PayloadMass"] = pd.to_numeric(
    df["PayloadMass"].astype(str).str.replace(r"[^\d.]", "", regex=True),
    errors="coerce",
)
mean_mass = df["PayloadMass"].mean()
df["PayloadMass"] = df["PayloadMass"].fillna(mean_mass)
print(f"Filled {df['PayloadMass'].isna().sum()} missing masses; mean {mean_mass:,.0f} kg")

# Orbit: collapse the parenthetical detail, e.g. 'LEO (ISS)' -> 'LEO'.
df["Orbit"] = df["Orbit"].astype(str).str.split("(").str[0].str.strip()

# LaunchSite: keep the pad, drop the base, e.g. 'Cape Canaveral, SLC-40' -> 'SLC-40'.
df["LaunchSite"] = (
    df["LaunchSite"].astype(str).str.split(",").str[-1].str.strip().str.replace("\u2011", "-")
)

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Year"] = df["Date"].dt.year

print("After engineering:", df.shape)
print("Overall landing success rate: {:.1%}".format(df["Class"].mean()))


# ----------------------------------------------------------------------------
# 1. Flight Number vs Launch Site
# ----------------------------------------------------------------------------
g = sns.catplot(data=df, x="FlightNumber", y="LaunchSite", hue="Class",
                aspect=2.5, height=4)
g.set_axis_labels("Flight number", "Launch site")
g.figure.suptitle("Flight number vs launch site (colour = landing outcome)", y=1.02)
g.savefig(f"{PLOT_DIR}/01_flightnumber_launchsite.png", dpi=120, bbox_inches="tight")
plt.close("all")


# ----------------------------------------------------------------------------
# 2. Payload Mass vs Launch Site
# ----------------------------------------------------------------------------
g = sns.catplot(data=df, x="PayloadMass", y="LaunchSite", hue="Class",
                aspect=2.5, height=4)
g.set_axis_labels("Payload mass (kg)", "Launch site")
g.figure.suptitle("Payload mass vs launch site", y=1.02)
g.savefig(f"{PLOT_DIR}/02_payloadmass_launchsite.png", dpi=120, bbox_inches="tight")
plt.close("all")


# ----------------------------------------------------------------------------
# 3. Success rate by orbit type
# ----------------------------------------------------------------------------
orbit_rate = df.groupby("Orbit")["Class"].agg(["mean", "size"]).sort_values("mean")
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(x=orbit_rate.index, y=orbit_rate["mean"], ax=ax)
for i, (rate, n) in enumerate(zip(orbit_rate["mean"], orbit_rate["size"])):
    ax.text(i, rate + 0.02, f"n={n}", ha="center", fontsize=8)
ax.set(xlabel="Orbit", ylabel="Landing success rate", ylim=(0, 1.12),
       title="Landing success rate by orbit type")
plt.xticks(rotation=45, ha="right")
fig.savefig(f"{PLOT_DIR}/03_success_rate_orbit.png", dpi=120, bbox_inches="tight")
plt.close("all")


# ----------------------------------------------------------------------------
# 4. Flight Number vs Orbit type
# ----------------------------------------------------------------------------
g = sns.catplot(data=df, x="FlightNumber", y="Orbit", hue="Class",
                aspect=2.5, height=5)
g.set_axis_labels("Flight number", "Orbit")
g.figure.suptitle("Flight number vs orbit type", y=1.02)
g.savefig(f"{PLOT_DIR}/04_flightnumber_orbit.png", dpi=120, bbox_inches="tight")
plt.close("all")


# ----------------------------------------------------------------------------
# 5. Payload Mass vs Orbit type
# ----------------------------------------------------------------------------
g = sns.catplot(data=df, x="PayloadMass", y="Orbit", hue="Class",
                aspect=2.5, height=5)
g.set_axis_labels("Payload mass (kg)", "Orbit")
g.figure.suptitle("Payload mass vs orbit type", y=1.02)
g.savefig(f"{PLOT_DIR}/05_payloadmass_orbit.png", dpi=120, bbox_inches="tight")
plt.close("all")


# ----------------------------------------------------------------------------
# 6. Yearly success trend
# ----------------------------------------------------------------------------
yearly = df.groupby("Year")["Class"].mean()
fig, ax = plt.subplots(figsize=(9, 5))
sns.lineplot(x=yearly.index, y=yearly.values, marker="o", ax=ax)
ax.set(xlabel="Year", ylabel="Landing success rate", ylim=(0, 1.05),
       title="Falcon 9 landing success rate by year")
fig.savefig(f"{PLOT_DIR}/06_yearly_trend.png", dpi=120, bbox_inches="tight")
plt.close("all")


# ----------------------------------------------------------------------------
# 7. Features -> one-hot -> float64
# ----------------------------------------------------------------------------
features = df[["FlightNumber", "PayloadMass", "Orbit", "LaunchSite",
               "BoosterVersion", "LandingPad", "Year"]].copy()

features_one_hot = pd.get_dummies(
    features,
    columns=["Orbit", "LaunchSite", "BoosterVersion", "LandingPad"],
)

features_one_hot = features_one_hot.astype("float64")

print("\nFeature matrix:", features_one_hot.shape)
print("All float64:", (features_one_hot.dtypes == np.float64).all())
print(features_one_hot.head())

features_one_hot.to_csv("spacex_features.csv", index=False)
df[["FlightNumber", "Date", "Class"]].to_csv("spacex_labels.csv", index=False)
print("\nWrote spacex_features.csv and spacex_labels.csv")
