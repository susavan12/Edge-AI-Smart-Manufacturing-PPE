import os
import shutil

# Original dataset
IMAGE_DIR = "dataset/images"
LABEL_DIR = "dataset/labels"

# New dataset
NEW_IMAGE_DIR = "dataset_filtered/images"
NEW_LABEL_DIR = "dataset_filtered/labels"

os.makedirs(NEW_IMAGE_DIR, exist_ok=True)
os.makedirs(NEW_LABEL_DIR, exist_ok=True)

# old_id -> new_id
CLASS_MAP = {
    0: 0,   # Excavator
    1: 1,   # Gloves
    2: 2,   # Hardhat
    4: 3,   # Mask
    5: 4,   # NO-Hardhat
    6: 5,   # NO-Mask
    7: 6,   # NO-Safety Vest
    8: 7,   # Person
    10: 8,  # Safety Cone
    11: 9   # Safety Vest
}

count_images = 0
count_labels = 0

for file in os.listdir(LABEL_DIR):

    if not file.endswith(".txt"):
        continue

    old_path = os.path.join(LABEL_DIR, file)

    new_lines = []

    with open(old_path, "r") as f:
        for line in f:
            parts = line.strip().split()

            if len(parts) < 5:
                continue

            cls = int(parts[0])

            if cls in CLASS_MAP:
                parts[0] = str(CLASS_MAP[cls])
                new_lines.append(" ".join(parts))

    if len(new_lines) == 0:
        continue

    new_label_path = os.path.join(NEW_LABEL_DIR, file)

    with open(new_label_path, "w") as f:
        f.write("\n".join(new_lines))

    image_name = os.path.splitext(file)[0]

    copied = False

    for ext in [".jpg", ".jpeg", ".png", ".webp"]:

        img = image_name + ext

        src = os.path.join(IMAGE_DIR, img)

        if os.path.exists(src):
            shutil.copy(src, os.path.join(NEW_IMAGE_DIR, img))
            copied = True
            break

    if copied:
        count_images += 1
        count_labels += 1

print("=" * 40)
print("Filtering Complete")
print("=" * 40)
print("Images :", count_images)
print("Labels :", count_labels)
print("Saved in dataset_filtered/")