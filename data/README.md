# Object-recognition dataset

`object_recognition/` contains ten CSV files with the schema:

```text
Label,Trial_ID,Time,S0,S1,S2,S3,S4
```

- `Trial_ID`: independent grasp number within the object class
- `Time`: time from the beginning of the trial, in seconds
- `S0`–`S4`: filtered resistance in ohms for thumb, index, middle, ring, and pinky channels

The release contains 30 trials per class and 40 frames per trial. It contains sensor measurements and object labels only; it does not contain names, images of participants, or other direct identifiers.

The dataset documents one controlled prototype evaluation. Users should collect additional participants, sessions, glove placements, and environmental conditions before drawing conclusions about generalization.
