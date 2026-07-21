from ultralytics import YOLO
import cv2

model = YOLO("best.pt")

image = cv2.imread("test.jpg")   # Use the same image you uploaded

results = model.predict(
    source=image,
    conf=0.25,
    imgsz=960,
    iou=0.45,
    save=True,
    show=False
)

print(results[0].boxes)