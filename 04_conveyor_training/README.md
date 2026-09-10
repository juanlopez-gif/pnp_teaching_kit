# Module 04 — Conveyor motion detection (moving / stopped)

Goal: for each belt, train a small model that says **is it moving or stopped**,
with a confidence value.

This is **not** YOLO. It uses **optical flow** (how pixels move between frames)
turned into 10 numbers, fed to a scikit-learn `GradientBoostingClassifier`, with
hysteresis so the state does not flicker.

## Which file when?

Both files are real and used. The difference is *train time* vs *run time*:

| File | When you use it | What it is |
|------|-----------------|------------|
| `train_conveyor.py` | **Once per belt, to create the model** | The interactive tool you run: draw ROI → record moving/stopped clips → train → test. |
| `conveyor_detector.py` | **Every time, at run time** | The `ConveyorDetector` class that *loads* a trained model and answers `moving? confidence?` on each frame. `train_conveyor.py` uses it too. |
| `models/<zone>/` | (data) | One trained model per belt (`classifier.pkl` + `roi.json`). Created on first save. |

So: you **train once** with `train_conveyor.py`; afterwards any program (including
the system logger in module 06) just imports `ConveyorDetector`, calls `.load()`,
and `.update(frame)` in its loop.

## Train a belt

```bash
python3 train_conveyor.py --zone conveyor2
```

`--zone` uses the zone names from `config.CAMERA_ZONES`; the tool automatically
picks the right camera index and model folder for that zone.

Menu order for a first run:
1. **Draw ROI** — outline just the belt surface (avoid background).
2. **Collect training data** — press `2`, then record several clips:
   `1`=STOPPED, `2`=RUNNING (also `6`=decelerating, `7`=accelerating).
   Get **at least 20 samples**, balanced between moving and stopped.
3. **Train** — prints a cross-validated F1 score. Aim for > 0.9.
4. **Live test** — watch it classify in real time. `q` to quit.

Everything is saved automatically to `models/<zone>/`.

## Use it in your own code

```python
from conveyor_detector import ConveyorDetector

det = ConveyorDetector(camera_id=4, model_dir="models/conveyor2")
det.load()
state = det.update(frame)      # or det.update() to read the camera itself
print(state.moving, state.confidence)
```

## Why optical flow instead of YOLO here?
"Moving vs stopped" is about *change between frames*, not *what object is where*.
Optical flow measures exactly that and needs only a handful of labelled clips —
far cheaper than labelling a detection dataset.
