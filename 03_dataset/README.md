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

## From images to a trained model — full workflow

The pipeline is: **capture here → label in Roboflow → train YOLO on a GPU
machine → bring `best.pt` back**. Step by step:

### Step 1 — Capture (this module)
```bash
python3 capture_dataset.py 0 4        # capture from the cameras you want
```
Aim for 150–300+ varied images: different piece positions across the whole ROI,
different lighting, and a few empty-belt frames. They land in `03_dataset/dataset/`.

### Step 2 — Label in Roboflow
1. Create a free account at **https://roboflow.com** → **Create New Project** →
   type **Object Detection**. Give the classes meaningful names (e.g.
   `red_square`, `blue_circle`) — these become the YOLO class names.
2. **Upload** the images from `03_dataset/dataset/` (drag the folder in).
3. **Annotate**: draw a bounding box around each piece and assign its class.
   Label *every* piece in *every* image; leave empty frames with no boxes.
4. **Generate a version**: set *Preprocessing → Resize to 640×640*. Optionally add
   a little augmentation (flip, brightness) to grow the set. Click **Generate**.
5. **Export**: *Versions → Export Dataset → Format = **YOLOv8** → "show download
   code"*. You get either a ZIP or a Python snippet like:
   ```python
   from roboflow import Roboflow
   rf = Roboflow(api_key="YOUR_KEY")
   project = rf.workspace("your-ws").project("your-project")
   dataset = project.version(1).download("yolov8")   # creates a folder with data.yaml
   ```

### Step 3 — Move the dataset to a machine with a GPU
Training YOLO on a CPU is painfully slow; use a machine with an NVIDIA GPU
(a lab PC, or Google Colab).

- **Option A — download straight on the GPU machine** with the Roboflow snippet
  above (needs `pip install roboflow`). Easiest.
- **Option B — copy the ZIP** from this PC:
  ```bash
  scp roboflow_export.zip user@gpu-host:~/pieces_dataset/
  ssh user@gpu-host 'cd ~/pieces_dataset && unzip roboflow_export.zip'
  ```

### Step 4 — Train YOLO on the GPU machine
```bash
pip install ultralytics
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"   # must print True

# data.yaml is the file inside the exported dataset folder
yolo detect train data=path/to/data.yaml model=yolov8n.pt epochs=100 imgsz=640 batch=16 device=0
```
- `model=yolov8n.pt` = nano (fast). Use `yolov8s.pt`/`yolov8m.pt` for more accuracy.
- `device=0` = first GPU. Results go to `runs/detect/train/`.
- Check `runs/detect/train/results.png` and the printed **mAP50** to judge quality.

### Step 5 — Bring the model back
```bash
scp user@gpu-host:~/runs/detect/train/weights/best.pt  ./best.pt
```
Then point the kit at it — `config.YOLO_MODEL_PATH` (default: `../best.pt`, i.e.
the project root). Now modules 05/06 detect your pieces.

## Tips for a good dataset
- Vary piece position across the whole belt/ROI.
- Vary lighting and include a few "empty belt" frames.
- Aim for a balanced number of examples per class (similar count each).
- Re-train with more images whenever the detector misses a case.
