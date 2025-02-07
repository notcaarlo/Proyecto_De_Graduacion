import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
import imutils
from PIL import Image
import numpy as np

# Cargar el modelo de ResNet para la clasificación de desechos
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_ft = models.resnet18(weights="IMAGENET1K_V1")
num_ftrs = model_ft.fc.in_features
model_ft.fc = nn.Linear(num_ftrs, 6)  # Asumiendo 6 clases de desechos
model_ft = model_ft.to(device)
model_ft.load_state_dict(torch.load("Modelos/modelo_resnet_finetuned.pth"))  # Cargar el modelo entrenado

# Transformaciones para la detección de desechos
data_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# Clasificación de los desechos
class_names = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']

# Umbral de confianza para las predicciones
confidence_threshold = 0.50  # Confianza como minimo

# Captura de Video y Procesamiento en Tiempo Real
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convertir a escala de grises y aplicar desenfoque para mejorar la detección de bordes
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Detectar bordes con Canny
    edged = cv2.Canny(blurred, 50, 150)

    # Encontrar contornos en la imagen
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        # Filtrar objetos pequeños
        if cv2.contourArea(contour) < 1000:
            continue

        # Obtener el rectángulo delimitador del contorno
        (x, y, w, h) = cv2.boundingRect(contour)

        # Extraer la región de interés (ROI) para la clasificación
        roi = frame[y:y+h, x:x+w]
        if roi.size == 0:
            continue

        # Preprocesamiento de la ROI
        input_image = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        input_image = Image.fromarray(input_image)
        input_image = data_transforms(input_image).unsqueeze(0).to(device)

        # Predicción del modelo
        with torch.no_grad():
            model_ft.eval()
            outputs = model_ft(input_image)
            softmax = torch.nn.Softmax(dim=1)
            probs = softmax(outputs)
            confidence, predicted_class = torch.max(probs, 1)
            predicted_class_name = class_names[predicted_class.item()]

        # Mostrar solo si la confianza es alta
        if confidence.item() >= confidence_threshold:
            label = f"{predicted_class_name}: {confidence.item() * 100:.2f}%"
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Mostrar el video con las predicciones
    cv2.imshow("Clasificación de Desechos", frame)

    # Salir presionando la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
