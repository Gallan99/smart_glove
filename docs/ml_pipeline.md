# Dataset and machine-learning pipeline

## Dataset

The included object-recognition dataset contains 300 static-grasp trials from 10 everyday-object classes:

- ball
- book
- bottle
- circular plastic object
- computer mouse
- multimeter
- pen
- ruler
- screwdriver
- smartphone

Each class contains 30 independent trials. A trial contains 40 synchronized S0–S4 frames sampled at 20 Hz, corresponding to a 2 s grasp window. Sensor values are stored in ohms.

The published 90% result is a single-user evaluation under the investigated protocol. It demonstrates separability of the recorded grasp signatures, not universal or person-independent performance. A separate second-participant experiment reported lower cross-user performance when training only on the first participant, which is why calibration and multi-user data collection are important next steps.

The committed CSV files are a curated, strongly session-specific snapshot. With the repository's default seed, a random 80/20 split of this snapshot can reach 100%. That reproducibility result verifies the software and the strong within-session class separation, but it is not a replacement for the reported 90% experimental result and must not be presented as independent generalization. A subject/session-held-out dataset is required for that claim.

## Features

For each 40-frame trial, the pipeline calculates two statistics per sensor:

```text
[mean(S0), mean(S1), mean(S2), mean(S3), mean(S4),
 std(S0),  std(S1),  std(S2),  std(S3),  std(S4)]
```

This produces a compact 10-element feature vector. Means encode the static finger configuration; standard deviations capture small within-grasp variations.

## Classifier

The default classifier is a Random Forest with 100 decision trees and random seed 42. The training command performs:

1. trial-level feature extraction;
2. a stratified 80/20 train-test split;
3. five-fold stratified cross-validation;
4. model serialization;
5. JSON metric export;
6. confusion-matrix generation.

The split is performed after trial aggregation, so individual frames from the same trial cannot be divided between training and test sets.

## Reproduce the evaluation

```bash
python -m pip install -e .
smart-glove-train
```

Generated files are written to `models/random_forest.joblib` and `results/generated/`. Generated model binaries are intentionally ignored because they can be reproduced from the committed dataset.

Only load `joblib` model files that you trust; Python model serialization is not a safe exchange format for untrusted files.

## Real-time inference

Real-time inference keeps the latest 40 valid frames in a sliding window, converts MΩ firmware output back to Ω, calculates the same ten features used during training, and reports the highest-probability class. By default, a prediction is displayed only above 55% confidence and is updated every five frames.
