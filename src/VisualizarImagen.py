import cv2
import torch
import torch.nn as nn
import torch.optim as optim
import torch.multiprocessing
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
import face_recognition
from scipy.spatial import distance
from imutils import face_utils
import dlib
import imutils
import os
from PIL import Image

# Función para calcular el Eye Aspect Ratio (EAR)
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

# Definición de la arquitectura del modelo de reconocimiento facial
class SimpleCNN(nn.Module):
    def __init__(self, num_classes=2):
        super(SimpleCNN, self).__init__()
        self.fc1 = nn.Linear(128, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, num_classes)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# Inicialización de Modelos
clf = SimpleCNN(num_classes=2)
clf.load_state_dict(torch.load("Modelos/modelo_cnn.pth"))
clf.eval()

# Cargar las etiquetas (nombres) desde el archivo labels.txt
labels_path = "Modelos/labels.txt"
with open(labels_path, "r") as f:
    y_labels = f.read().splitlines()  # Leer todas las líneas y almacenarlas como una lista

# Detector de rostros y predicción de landmarks faciales con dlib
detect = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("Modelos/shape_predictor_68_face_landmarks.dat")

# Índices de los landmarks para los ojos
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

# Parámetros para la detección de somnolencia
thresh = 0.25  # Umbral para el EAR
frame_check = 20  # Frames continuos para activar la alerta
contador_somnolencia = 0  # Contador de frames con somnolencia

# Captura de Video y Procesamiento en Tiempo Real
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = imutils.resize(frame, width=600)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detección de rostros para el reconocimiento facial
    caras = face_recognition.face_locations(rgb_frame)
    embeddings = face_recognition.face_encodings(rgb_frame, caras)

    # Detección de rostros para la somnolencia con dlib
    subjects = detect(gray, 0)

    for (top, right, bottom, left), embedding in zip(caras, embeddings):
        # Reconocimiento facial
        with torch.no_grad():
            embedding_tensor = torch.tensor(embedding, dtype=torch.float32).unsqueeze(0)
            output = clf(embedding_tensor)
            prediccion = torch.argmax(output, dim=1).item()

            # Obtener el nombre correspondiente a la predicción
            nombre_predicho = y_labels[prediccion]  # Usar el índice para obtener el nombre

        # Detección de somnolencia
        rect = dlib.rectangle(left, top, right, bottom)
        shape = predict(gray, rect)
        shape = face_utils.shape_to_np(shape)

        # Extraer los ojos
        leftEye = shape[lStart:lEnd]
        rightEye = shape[rStart:rEnd]
        leftEAR = eye_aspect_ratio(leftEye)
        rightEAR = eye_aspect_ratio(rightEye)
        ear = (leftEAR + rightEAR) / 2.0

        # Dibujar contornos de los ojos
        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

        # Mostrar el nombre de la persona
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        # Mostrar el nombre
        cv2.putText(frame, f"{nombre_predicho}", (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3, cv2.LINE_AA) # Color del nombre

        # Verificar somnolencia si el EAR está por debajo del umbral
        if ear < thresh:
            contador_somnolencia += 2.5
            if contador_somnolencia >= frame_check:
                cv2.rectangle(frame, (40, 20), (560, 70), (0, 0, 255), 2)
                cv2.putText(frame, "!ALERTA DE SOMNOLENCIA!", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4, cv2.LINE_AA)
        else:
            contador_somnolencia = 0

    # Mostrar el video con resultados
    cv2.imshow("Reconocimiento Facial + Detección de Somnolencia", frame)

    # Salir presionando la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
