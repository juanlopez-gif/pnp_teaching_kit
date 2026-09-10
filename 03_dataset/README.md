# Module 03 — Dataset capture

Goal: collect images to train (or improve) the YOLO piece detector.

## Script

| Script | What it does |
|--------|--------------|
| `capture_dataset.py` | Shows all cameras, saves a synchronized snapshot from each on SPACE. |

## Use

```bash
python3 capture_dataset.py            # all cameras from config.CAMERA_ZONES
python3 capture_dataset.py 0 4        # only the cameras you choose
python3 capture_dataset.py --out red_pieces 0 4   # custom output folder
# SPACE = save one frame per camera   |   q = quit
```

Images land in `03_dataset/<out>/` (default `dataset/`) named
`cam<INDEX>_<TIMESTAMP>_<COUNTER>.jpg`.

## From images to a trained model

This kit does not include the labelling/training step for YOLO (that is done
with an external tool), but the flow is:

1. Capture varied images here (different pieces, positions, lighting).
2. Label the pieces (bounding box + class) with e.g. **Roboflow**, **CVAT**, or **LabelImg**.
3. Train YOLO:
   ```bash
   yolo detect train data=dataset.yaml model=yolov8n.pt epochs=100 imgsz=640
   ```
4. Copy the resulting `best.pt` and point `config.YOLO_MODEL_PATH` at it.

## Tips for a good dataset
- Vary piece position across the whole belt/ROI.
- Vary lighting and include a few "empty belt" frames.
- Aim for a balanced number of examples per class.
