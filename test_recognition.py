import cv2

from face_recognition import EmployeeRecognizer

recognizer = EmployeeRecognizer()

image = cv2.imread("employee_faces/EMP100.jpg")

if image is None:
    print("Image not found.")
else:
    print(recognizer.recognize(image))