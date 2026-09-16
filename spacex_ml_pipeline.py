"""
Falcon 9 first-stage landing prediction pipeline.

Input:  spacex_launch_geo.csv (77 launches, 2010-06-04 to 2019-12-17)
Output: printed EDA summary, spacex_ml_features.csv, spacex_model_comparison.png,
        and a saved best model (best_model.joblib)

Requirements: pandas, numpy, scikit-learn, matplotlib, joblib
"""

import warnings

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, classification_report
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore", category=FutureWarning)

RANDOM_STATE = 2  # fixed for reproducibility, small-sample study

# ----------------------------------------------------------------------------
# Load
# ----------------------------------------------------------------------------
df = pd.read_csv("spacex_launch_geo.csv")
print(f"Loaded {len(df)} launches, {df['class'].sum()} successful landings "
      f"({df['class'].mean():.1%})\n")


# ----------------------------------------------------------------------------
# EDA relevant to the modelling question
# ----------------------------------------------------------------------------
print("=" * 70)
print("EDA: landing success rate by categorical feature")
print("=" * 70)
for col in ["LaunchSite", "Orbit", "BoosterVersion"]:
    print(f"\n-- {col} --")
    print(df.groupby(col)["class"].agg(["count", "mean"]).sort_values("mean", ascending=False))

print(f"\nMissing PayloadMassKG: {df['PayloadMassKG'].isna().sum()} rows "
      f"(classified payloads: {df.loc[df['PayloadMassKG'].isna(), 'Payload'].tolist()})")

print(f"\nFlight number vs class correlation: "
      f"{df['FlightNumber'].corr(df['class']):.3f}  (later flights land more often, as expected)")


# ----------------------------------------------------------------------------
# Training labels
# ----------------------------------------------------------------------------
# 'class' was set when spacex_launch_geo.csv was built: 1 if LandingOutcome
# starts with 'Success' (ground pad or drone ship), 0 for every failure, no
# attempt, precluded, or deliberate controlled-descent test. That is the
# target (Y) for this pipeline; nothing further to derive here.
Y = df["class"].astype("float64")


# ----------------------------------------------------------------------------
# Feature engineering (mirrors the earlier EDA notebook)
# ----------------------------------------------------------------------------
features = df[["FlightNumber", "PayloadMassKG", "Orbit", "LaunchSite", "BoosterVersion"]].copy()
features["PayloadMassKG"] = features["PayloadMassKG"].fillna(features["PayloadMassKG"].mean())

X = pd.get_dummies(features, columns=["Orbit", "LaunchSite", "BoosterVersion"])
X = X.astype("float64")
X.to_csv("spacex_ml_features.csv", index=False)
print(f"\nFeature matrix: {X.shape[0]} rows x {X.shape[1]} columns")


# ----------------------------------------------------------------------------
# Standardize
# ----------------------------------------------------------------------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)


# ----------------------------------------------------------------------------
# Train/test split
# ----------------------------------------------------------------------------
X_train, X_test, Y_train, Y_test = train_test_split(
    X_scaled, Y, test_size=0.2, random_state=RANDOM_STATE
)
print(f"Train: {X_train.shape[0]} rows | Test: {X_test.shape[0]} rows "
      f"(test set is small — treat accuracy differences of 1 sample, ~{100/len(Y_test):.0f} "
      f"percentage points, as within noise)")


# ----------------------------------------------------------------------------
# Hyperparameter search: Logistic Regression, SVM, Decision Tree
# ----------------------------------------------------------------------------
results = {}

print("\n" + "=" * 70)
print("Logistic Regression")
print("=" * 70)
lr_params = {
    "C": [0.01, 0.1, 1, 10, 100],
    "penalty": ["l2"],
    "solver": ["lbfgs", "liblinear"],
}
lr_cv = GridSearchCV(LogisticRegression(max_iter=1000), lr_params, cv=5, scoring="accuracy")
lr_cv.fit(X_train, Y_train)
print("Best params:", lr_cv.best_params_)
print(f"Best CV accuracy: {lr_cv.best_score_:.3f}")
results["Logistic Regression"] = lr_cv

print("\n" + "=" * 70)
print("Support Vector Machine")
print("=" * 70)
svm_params = {
    "kernel": ["linear", "rbf", "poly", "sigmoid"],
    "C": [0.01, 0.1, 1, 10, 100],
    "gamma": ["scale", "auto", 0.01, 0.1, 1],
}
svm_cv = GridSearchCV(SVC(), svm_params, cv=5, scoring="accuracy")
svm_cv.fit(X_train, Y_train)
print("Best params:", svm_cv.best_params_)
print(f"Best CV accuracy: {svm_cv.best_score_:.3f}")
results["SVM"] = svm_cv

print("\n" + "=" * 70)
print("Decision Tree")
print("=" * 70)
tree_params = {
    "criterion": ["gini", "entropy"],
    "splitter": ["best", "random"],
    "max_depth": [2, 4, 6, 8, 10, None],
    "max_features": ["sqrt", "log2", None],
    "min_samples_leaf": [1, 2, 4],
    "min_samples_split": [2, 5, 10],
}
tree_cv = GridSearchCV(
    DecisionTreeClassifier(random_state=RANDOM_STATE), tree_params, cv=5, scoring="accuracy"
)
tree_cv.fit(X_train, Y_train)
print("Best params:", tree_cv.best_params_)
print(f"Best CV accuracy: {tree_cv.best_score_:.3f}")
results["Decision Tree"] = tree_cv


# ----------------------------------------------------------------------------
# Compare on the held-out test set
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("Test-set performance")
print("=" * 70)

test_scores = {}
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
for ax, (name, cv) in zip(axes, results.items()):
    pred = cv.predict(X_test)
    acc = accuracy_score(Y_test, pred)
    test_scores[name] = acc
    print(f"\n{name}: test accuracy = {acc:.3f}")
    print(classification_report(Y_test, pred, target_names=["No landing", "Landing"]))
    ConfusionMatrixDisplay.from_predictions(
        Y_test, pred, display_labels=["No landing", "Landing"], ax=ax, colorbar=False
    )
    ax.set_title(f"{name}\ntest acc = {acc:.3f}")

fig.tight_layout()
fig.savefig("spacex_model_comparison.png", dpi=130, bbox_inches="tight")

best_name = max(test_scores, key=test_scores.get)
best_model = results[best_name].best_estimator_
print(f"\n{'='*70}\nBest model on the test set: {best_name} ({test_scores[best_name]:.3f} accuracy)")
print(f"CV accuracy for comparison: {results[best_name].best_score_:.3f}")
print("=" * 70)

joblib.dump({"model": best_model, "scaler": scaler, "feature_columns": list(X.columns)},
            "best_model.joblib")
print("\nSaved best_model.joblib (model + scaler + feature column order)")
