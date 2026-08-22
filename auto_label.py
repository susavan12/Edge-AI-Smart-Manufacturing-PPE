from ultralytics import YOLO
from pathlib import Path

# ===========================
# Load Model
# ===========================

model = YOLO("best.pt")

# ===========================
# Dataset Paths
# ===========================

IMAGE_DIR = Path("dataset/images")
LABEL_DIR = Path("dataset/labels")

LABEL_DIR.mkdir(parents=True, exist_ok=True)

# ===========================
# Class Mapping
# Old Class ID -> New Class ID
# ===========================

CLASS_MAP = {

    8: 0,    # Person

    2: 1,    # Hardhat

    11: 2,   # Safety Vest

    5: 3,    # NO-Hardhat

    7: 4     # NO-Safety Vest

}

# ===========================
# Confidence Threshold
# ===========================

CONF = 0.30

# ===========================
# Supported Image Types
# ===========================

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

# ===========================
# Counter
# ===========================

total_images = 0
total_labels = 0

# ===========================
# Process Images
# ===========================

for image_path in IMAGE_DIR.iterdir():

    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        continue

    total_images += 1

    results = model.predict(
        source=str(image_path),
        conf=CONF,
        verbose=False
    )

    result = results[0]

    label_file = LABEL_DIR / f"{image_path.stem}.txt"

    with open(label_file, "w") as f:

        for box in result.boxes:

            cls = int(box.cls[0])

            if cls not in CLASS_MAP:
                continue

            new_cls = CLASS_MAP[cls]

            x, y, w, h = box.xywhn[0].tolist()

            f.write(
                f"{new_cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"
            )

            total_labels += 1

print("\n============================")
print("Auto Label Complete")
print("============================")
print("Images Processed :", total_images)
print("Objects Labeled  :", total_labels)
print("Labels Saved To  :", LABEL_DIR)