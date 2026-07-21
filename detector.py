from ultralytics import YOLO


class PPEDetector:

    def __init__(self):
        # Load trained model
        self.model = YOLO("best.pt")

        print(self.model.names)
        print(self.model.ckpt_path)

    def detect(self, image):

        results = self.model.predict(

            source=image,

            # Lower confidence for stable webcam detection
            conf=0.25,

            # NMS threshold
            iou=0.45,

            # High resolution
            imgsz=960,

            # Allow more detections
            max_det=100,

            augment=False,

            verbose=False,

            save=False,

            half=False,

            stream=False,
        

        )

        return results