# Module 02 — ROIs (Regions of Interest)

Goal: draw and name the areas each camera should care about.

An **ROI** is a named polygon on a camera image. A detection only "counts" if
its centre lands inside an ROI. This is how one camera can watch several things
(e.g. a belt plus a buffer zone) and keep them separate.

## Scripts

| Script | What it does |
|--------|--------------|
| `define_rois.py` | Live multi-camera editor. Draw polygons, name them, save to `rois.json`. |

`rois.example.json` shows the expected file format (copy it to `rois.json` to
start from something, or just draw from scratch).

## How to use

```bash
python3 define_rois.py
```

- **Left click** to drop polygon vertices on any camera tile.
- **Right click** or **ENTER** to close the polygon, then **type a name** and press ENTER.
- **z** undo, **c** clear the camera you last clicked, **s** save, **q** save & quit.

## File format

`rois.json` (path set by `config.ROIS_PATH`) is keyed by camera index:

```json
{
  "0": [ { "pts": [[x, y], ...], "name": "conveyor4" } ],
  "4": [ { "pts": [[x, y], ...], "name": "conveyor2" } ]
}
```

## Naming convention

Give ROIs the **zone names** from `config.CAMERA_ZONES` (`conveyor1`..`conveyor4`)
so the rest of the kit can line up a camera, its ROI, and its motion model
automatically.
