import cv2
import torch
import torch.nn as nn
import imutils
import os
from PIL import Image
import dlib
from scipy.spatial import distance
from imutils import face_utils
import face_recognition
import numpy as np
import torchvision.models as models
import torchvision.transforms as transforms

# Función para calcular el Eye Aspect Ratio (EAR)
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

# Definición de la arquitectura del modelo de reconocimiento facial
class FaceRecognitionCNNLSTM(nn.Module):
    def __init__(self, input_size=512, hidden_size=128, num_layers=2, num_classes=2):
        super(FaceRecognitionCNNLSTM, self).__init__()

        # Cargar un modelo ResNet pre-entrenado (sin la capa fully connected final)
        resnet = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        self.resnet = nn.Sequential(*list(resnet.children())[:-1])  # Eliminar la capa final (fully connected)

        # Capa LSTM
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)

        # Capa de clasificación
        self.fc1 = nn.Linear(hidden_size, 128)  # Cambiar a hidden_size
        self.fc2 = nn.Linear(128, num_classes)  # Número de clases

        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        # Pasar la entrada a través de ResNet para obtener las características
        x = self.resnet(x)
        x = x.view(x.size(0), -1)  # Aplanar el resultado

        # Asegurarse de que la entrada al LSTM tenga la forma correcta
        x = x.unsqueeze(1)  # Añadir dimensión de secuencia para LSTM (batch_size, 1, input_size)

        # Luego pasar las características a través del LSTM
        out, (hn, cn) = self.lstm(x)  # Ahora la entrada tiene forma (batch_size, 1, 512)
        out = out[:, -1, :]  # Tomar solo la salida de la última capa del LSTM

        out = self.dropout(out)
        out = torch.relu(self.fc1(out))
        out = self.fc2(out)
        return out


# Crear una instancia del modelo
clf = FaceRecognitionCNNLSTM()

# Intentamos cargar el modelo guardado ignorando las capas faltantes
try:
    clf.load_state_dict(torch.load("Modelos/modelo_cnn_lstm.pth"), strict=False)
    print("Modelo cargado correctamente.")
except RuntimeError as e:
    print("Error al cargar el modelo:", e)

# Cargar las etiquetas (nombres)
with open("Modelos/labels.txt", "r") as f:
    y_labels = f.read().splitlines()

# Verificar que el número de clases coincida con las etiquetas
print("Número de clases en el modelo:", clf.fc2.out_features)
print("Número de etiquetas cargadas:", len(y_labels))

# Detector de rostros y predicción de landmarks
detect = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("Modelos/shape_predictor_68_face_landmarks.dat")
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

# Parámetros para la detección de somnolencia
thresh = 0.25
frame_check = 20
contador_somnolencia = 0

# Transformación para la entrada de la red ResNet
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Captura de Video
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error al abrir la cámara.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = imutils.resize(frame, width=600)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    caras = detect(gray, 0)

    for rect in caras:
        (x, y, w, h) = (rect.left(), rect.top(), rect.width(), rect.height())
        rostro = frame[y:y + h, x:x + w]
        
        if rostro.size == 0:  # Verifica si el rostro está vacío
            continue

        # Preprocesamiento de la imagen
        rostro_rgb = cv2.cvtColor(rostro, cv2.COLOR_BGR2RGB)
        rostro_pil = Image.fromarray(rostro_rgb)
        rostro_resized = rostro_pil.resize((224, 224))  # Redimensionar al tamaño esperado
        rostro_resized = transform(rostro_resized).unsqueeze(0)  # [1, 3, 224, 224]

        # Obtener las características de la imagen (pasar la imagen por la CNN y luego por el LSTM)
        with torch.no_grad():
            features = clf(rostro_resized)

        # Realizar la predicción
        prediccion = torch.argmax(features, dim=1).item()

        # Verificar que la predicción esté dentro del rango de clases
        nombre_predicho = y_labels[prediccion] if prediccion < len(y_labels) else "Desconocido"
        
        # Detección de somnolencia
        shape = predict(gray, rect)
        shape = face_utils.shape_to_np(shape)
        leftEAR = eye_aspect_ratio(shape[lStart:lEnd])
        rightEAR = eye_aspect_ratio(shape[rStart:rEnd])
        ear = (leftEAR + rightEAR) / 2.0

        if ear < thresh:
            contador_somnolencia += 1
            if contador_somnolencia >= frame_check:
                cv2.putText(frame, "!ALERTA DE SOMNOLENCIA!", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4, cv2.LINE_AA)
        else:
            contador_somnolencia = 0

        # Dibujar contorno alrededor de ambos ojos
        # Ojo izquierdo
        left_eye = shape[lStart:lEnd]
        for (i, j) in zip(range(len(left_eye)), range(1, len(left_eye) + 1)):
            cv2.line(frame, tuple(left_eye[i]), tuple(left_eye[j % len(left_eye)]), (0, 255, 255), 2)
        
        # Ojo derecho
        right_eye = shape[rStart:rEnd]
        for (i, j) in zip(range(len(right_eye)), range(1, len(right_eye) + 1)):
            cv2.line(frame, tuple(right_eye[i]), tuple(right_eye[j % len(right_eye)]), (0, 255, 255), 2)

        # Fondo semi-transparente detrás del nombre (simulación de opacidad)
        overlay = frame.copy()
        alpha = 0.6  # Opacidad
        cv2.rectangle(overlay, (x, y - 30), (x + w, y), (0, 0, 0), -1)  # Fondo negro
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Mostrar el nombre con un fondo
        cv2.putText(frame, nombre_predicho, (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

        # Mostrar el nombre y el rectángulo
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.imshow("Reconocimiento + Somnolencia", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
