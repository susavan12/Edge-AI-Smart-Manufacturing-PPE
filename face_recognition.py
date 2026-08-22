import os
import cv2
import numpy as np
import insightface


class EmployeeRecognizer:

    def __init__(self):

        self.app = insightface.app.FaceAnalysis()

        self.app.prepare(ctx_id=-1)

        self.employee_db = {}

        self.load_database()

    def load_database(self):

        folder = "employee_faces"

        self.employee_db = {}

        if not os.path.exists(folder):
            print("employee_faces folder not found.")
            return

        for file in os.listdir(folder):

            path = os.path.join(folder, file)

            image = cv2.imread(path)

            if image is None:
                print("Cannot read:", file)
                continue

            faces = self.app.get(image)

            print(file, "Faces Found =", len(faces))

            if len(faces) == 0:
                print("No face detected in", file)
                continue

            employee_id = os.path.splitext(file)[0]

            self.employee_db[employee_id] = faces[0].embedding

            print("Loaded:", employee_id)

        print("Loaded Employees:", list(self.employee_db.keys()))

    def recognize(self, image):

        faces = self.app.get(image)

        if len(faces) == 0:
            return "Unknown"

        unknown = faces[0].embedding

        best_name = None
        best_score = -1

        for name, emb in self.employee_db.items():

            score = np.dot(unknown, emb) / (
                np.linalg.norm(unknown) *
                np.linalg.norm(emb)
            )

            if score > best_score:
                best_score = score
                best_name = name

        print("Best Match:", best_name, " Score:", best_score)

        if best_score > 0.30:
            return best_name

        return "Unknown"