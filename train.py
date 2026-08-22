from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(
    data="dataset_filtered/data.yaml",
    epochs=100,
    imgsz=640,
    batch=8,
    workers=2,
    device="cpu",
    project="runs",
    name="PPE_MultiWorker"
)