# VMS recording SOP: what the system checks

<!-- Generated from backend/vms/analysis/rubrics/*.yaml by `python -m vms.cli sop-doc --out docs/SOP.md`. Don't edit by hand. -->

Every parcel you pack or unbox is filmed. That video is the evidence when a customer says an item was missing, wrong, damaged, or had its tags removed. The system watches each video and scores it out of 100 against the steps below.

- **Pass:** every step was clearly shown. Nothing more to do.
- **Review:** something was unclear. A reviewer watches the video and decides.
- **Fail:** important steps were missing. The video may not protect you in a dispute.

The system is cautious. When it is unsure, it asks a person instead of passing the video. A reviewer can overturn its decision, and every decision is recorded.

## Rules that apply to every video

- If fewer than half the frames are usable (too dark or blurry), the video can't pass. It goes to a reviewer at best.
- If the barcode is never read, the video can't pass. It goes to a reviewer at best.
- A video shorter than 3 seconds always fails.

## How to film so it passes

- Record at 720p or better, in good light. Avoid backlight from windows.
- Keep the camera steady (a fixed mount is best) and the work area clear.
- Hold every label and tag close to the lens, in focus, for at least 2 seconds.
- Record one parcel per video, start to finish, without cutting or pausing.
- Keep your hands from covering the barcode while it is in view.

## Forward (Packing) SOP

Rubric `forward-v1`. A video passes with **85 or more points** out of 100 when the system is confident; 50–84 points, or low confidence, sends it to a reviewer; below 50 fails.

### Step 1. Shipping Label & Barcode (30 points)

**What to show:** Label clearly visible, barcode readable before sealing.

| The system looks for | Points | If it's missed |
|---|---|---|
| Readable printed text on the label | 10 | No clear text/label detected. Hold label closer. |
| The label held still in view (at least 2.0 s) | 5 | Label not held steady for 2 seconds. |
| The AWB barcode decoded by the system | 15 | Barcode not read. Ensure it is in focus. |

### Step 2. Packing & Sealing (20 points)

**What to show:** Item packed correctly, bag/box sealed fully on camera.

| The system looks for | Points | If it's missed |
|---|---|---|
| The parcel visible for most of the video | 8 | Package not consistently visible. |
| Sealing activity in the last part of the video | 6 | No sealing activity seen at the end of the video. |
| A recording long enough to show the whole process (longer than 10 s) | 6 | Video too short for full process. |

### Step 3. Brand Tag & Hangtag (25 points)

**What to show:** Brand tags attached and visible before packing.

| The system looks for | Points | If it's missed |
|---|---|---|
| Brand tags or hangtags in view | 15 | Brand tag not detected clearly. |
| Readable text on the tags | 10 | Tag text not readable. |

### Step 4. Product Condition (25 points)

**What to show:** Item unfolded and inspected for defects before packing.

| The system looks for | Points | If it's missed |
|---|---|---|
| The product itself, unfolded and in view | 25 | Product not visible enough. |

## Return (Unboxing) SOP

Rubric `return-v1`. A video passes with **85 or more points** out of 100 when the system is confident; 50–84 points, or low confidence, sends it to a reviewer; below 50 fails.

### Step 1. Shipping Label & Barcode (30 points)

**What to show:** Outer AWB label held clearly toward camera before opening.

| The system looks for | Points | If it's missed |
|---|---|---|
| Readable printed text on the label | 10 | No clear text/label detected. Hold label closer. |
| The label held still in view (at least 2.0 s) | 5 | Label not held steady for 2 seconds. |
| The AWB barcode decoded by the system | 15 | Barcode not read. Ensure it is in focus. |

### Step 2. Package Seal & Unboxing (20 points)

**What to show:** Seal inspected for tampering, package opened fully on camera, all 6 sides shown.

| The system looks for | Points | If it's missed |
|---|---|---|
| The parcel visible for most of the video | 6 | Package not consistently visible. |
| All six sides of the parcel turned toward the camera (6 sides) | 10 | Show all 6 sides of the package before opening. Partial points available. |
| A recording long enough to show the whole process (longer than 10 s) | 4 | Video too short for full process. |

### Step 3. Brand Tag & Hangtag (25 points)

**What to show:** Brand labels and price tags shown close to camera.

| The system looks for | Points | If it's missed |
|---|---|---|
| Brand tags or hangtags in view | 15 | Brand tag not detected clearly. |
| Readable text on the tags | 10 | Tag text not readable. |

### Step 4. Product Condition (25 points)

**What to show:** Item fully unfolded, both sides shown, checked for damage or fraud.

| The system looks for | Points | If it's missed |
|---|---|---|
| The product itself, unfolded and in view | 20 | Product not visible enough. |
| The product turned over to show both sides (turned over at least 2 times) | 5 | Turn the product to show both sides. Partial points available. |
