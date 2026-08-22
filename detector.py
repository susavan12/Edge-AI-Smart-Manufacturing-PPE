from ultralytics import YOLO


class PPEDetector:

    def __init__(self):
        # Load trained model
        self.model = YOLO("best_v2.pt")
        self.model.to("cpu")

        print(self.model.names)
        print(self.model.ckpt_path)

    def detect(self, image):

        results = self.model.predict(

            source=image,

            conf=0.25,

            iou=0.45,

            imgsz=640,

            max_det=20,

            augment=False,

            verbose=True,

            save=False,

            stream=False

        )

        return results