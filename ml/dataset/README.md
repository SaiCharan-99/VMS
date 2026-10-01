# Annotation guide: VMS detector dataset

Goal: a YOLOv8 model that finds the things the SOP asks operators to show. The analyzer turns the
boxes into rubric metrics (`seal_visible_ratio`, `tag_close_up_ratio`, ...), so **consistent
labelling matters more than volume**.

## 1. Get frames

```powershell
python ml/extract_frames.py --input data/samples --every-seconds 1 --max-per-video 60
```

Frames go to `data/frames/<video>/`. Near-identical frames are dropped automatically.
Take frames from **many different videos** (operators, stations, lighting, brands) rather than
many frames from a few videos. Include bad footage too (dim, blurred, partly hidden objects).

## 2. Annotate

Use **CVAT** (self-hosted or cvat.ai) or **Roboflow**. Draw tight axis-aligned boxes and export as
**YOLO 1.1 / YOLOv8** with the class order in `ml/data.yaml`. Aim for **at least 300 boxes per
class** (more for `brand_tag`, `hangtag` and `seal_tape`, which vary the most) before the first
training run.

| Class | Draw a box around | Do not label |
|---|---|---|
| `shipping_label` | The whole printed AWB / courier label | A label on a different parcel in the background |
| `barcode` | The barcode or QR itself, quiet zone excluded | Barcodes on product packaging that is not the AWB |
| `brand_tag` | The sewn-in or printed brand / size label | Care-instruction ribbons, unless that is the brand tag |
| `hangtag` | The paper or plastic tag hanging from the item (price, brand) | Stickers on the polybag |
| `product` | The garment or item, as far as it is visible | The hands holding it |
| `package_box` | The outer carton | The table or tray |
| `package_polybag` | The courier polybag / flyer | A polybag around the product itself (that is `product`) |
| `seal_tape` | Tape or the adhesive strip on a seam, visible and unbroken or cut | Loose tape on the table |
| `hand` | Each visible hand (with glove) | Forearms |
| `scissors_cutter` | Scissors, cutter or knife | Pens, phones |

Rules:

- Label an object if **at least about 30 % is visible**; skip anything smaller or unreadable.
- Overlap is fine (a `hand` over a `product`; a `barcode` inside a `shipping_label`).
- Label every instance in the frame, not only the best one. Missing boxes teach the model that the object is background.
- Do not label blurred beyond recognition frames. Delete them.
- Two people labelling the same 50 frames should agree on about 90 % of boxes. Check this before scaling up.

## 3. Split by video

Put **whole videos** in either `train` or `val` (about 80/20). Frames of one video in both
sets inflate mAP and hide real problems.

```
data/yolo/images/train/*.jpg   data/yolo/labels/train/*.txt
data/yolo/images/val/*.jpg     data/yolo/labels/val/*.txt
```

Copy `ml/data.yaml` to `data/yolo/data.yaml`.

## 4. Train and use

```powershell
pip install -e "backend[ml]"
python ml/train.py --data data/yolo/data.yaml --model yolov8s.pt --epochs 80
```

This writes `data/models/vms-det-<date>.pt` and `vms-det-<date>.model_card.json` (metrics,
classes, class-to-role map, dataset hash). Then:

```powershell
$env:VMS_YOLO_WEIGHTS = "data/models/vms-det-<date>.pt"
python ml/evaluate.py --labels data/eval/labels.csv --rubric return-v2
```

The analyzer reads the model card beside the weights, so no code change is needed. Compare
v1 on the old weights against v2 on the new ones with `ml/evaluate.py`, and keep v2 only if the
**false-pass rate** does not go up.

Never commit images, labels, `*.pt` files (they are gitignored under `data/`).
