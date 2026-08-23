"""Train and evaluate the Random Forest object-recognition model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from ml.features import FEATURE_NAMES, load_dataset


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/object_recognition"))
    parser.add_argument("--model", type=Path, default=Path("models/random_forest.joblib"))
    parser.add_argument("--results", type=Path, default=Path("results/generated"))
    parser.add_argument("--trees", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    features, labels, sources = load_dataset(args.data)
    classes, counts = np.unique(labels, return_counts=True)
    if len(classes) < 2 or counts.min() < 5:
        raise SystemExit("Training requires at least two classes and five trials per class")

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.2,
        random_state=args.seed,
        stratify=labels,
    )
    model = RandomForestClassifier(n_estimators=args.trees, random_state=args.seed, n_jobs=-1)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    holdout_accuracy = float(accuracy_score(y_test, predictions))

    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed)
    cv_scores = cross_val_score(model, features, labels, cv=folds, scoring="accuracy", n_jobs=-1)

    args.model.parent.mkdir(parents=True, exist_ok=True)
    args.results.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "window_size": 40,
        "resistance_unit": "ohm",
        "classes": classes.tolist(),
        "training_samples": len(features),
        "random_seed": args.seed,
    }
    joblib.dump(bundle, args.model)

    matrix = confusion_matrix(y_test, predictions, labels=classes)
    plt.figure(figsize=(11, 9))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Greens", xticklabels=classes, yticklabels=classes)
    plt.title(f"Random Forest confusion matrix — accuracy {holdout_accuracy:.1%}")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    figure_path = args.results / "confusion_matrix.png"
    plt.savefig(figure_path, dpi=180)
    plt.close()

    metrics = {
        "classes": classes.tolist(),
        "trials_per_class": dict(zip(classes.tolist(), counts.astype(int).tolist())),
        "feature_count": int(features.shape[1]),
        "holdout_accuracy": holdout_accuracy,
        "cross_validation_accuracy_mean": float(cv_scores.mean()),
        "cross_validation_accuracy_std": float(cv_scores.std()),
        "cross_validation_scores": cv_scores.tolist(),
        "model_path": str(args.model),
        "confusion_matrix_path": str(figure_path),
        "source_trial_count": len(sources),
    }
    (args.results / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Trials: {len(features)} across {len(classes)} classes")
    print(f"Holdout accuracy: {holdout_accuracy:.2%}")
    print(f"5-fold CV: {cv_scores.mean():.2%} +/- {cv_scores.std():.2%}")
    print(f"Model: {args.model}")


if __name__ == "__main__":
    main()
