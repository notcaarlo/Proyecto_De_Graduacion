import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
import imutils
from PIL import Image

# Cargar el modelo de ResNet para la clasificación de desechos
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_ft = models.resnet18(weights="IMAGENET1K_V1")
num_ftrs = model_ft.fc.in_features
model_ft.fc = nn.Linear(num_ftrs, 6)  # Asumiendo 6 clases de desechos
model_ft = model_ft.to(device)
model_ft.load_state_dict(torch.load("Modelos/modelo_resnet_finetuned.pth"))  # Cargar el modelo entrenado (con fine-tuning)

# Transformaciones para la detección de desechos
data_transforms = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# Clasificación de los desechos
class_names = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']

# Umbral de confianza para las predicciones
confidence_threshold = 0.85  # 85% de confianza como mínimo para aceptar la predicción

# Captura de Video y Procesamiento en Tiempo Real
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = imutils.resize(frame, width=600)

    # Convertir el frame a formato RGB y a tamaño adecuado
    input_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_image = cv2.resize(input_image, (224, 224))  # Cambiar el tamaño a 224x224 para ResNet
    input_image = Image.fromarray(input_image)

    # Aplicar las transformaciones
    input_image = data_transforms(input_image).unsqueeze(0).to(device)

    # Hacer la predicción de los desechos
    with torch.no_grad():
        model_ft.eval()
        outputs = model_ft(input_image)
        softmax = torch.nn.Softmax(dim=1)
        probs = softmax(outputs)
        confidence, predicted_class = torch.max(probs, 1)
        predicted_class_name = class_names[predicted_class.item()]

    # Mostrar si la predicción no es confiable
    if confidence.item() < confidence_threshold:
        cv2.putText(frame, "Error, intente de nuevo", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
    else:
        # Mostrar la predicción de desechos
        cv2.putText(frame, f"Desecho: {predicted_class_name} ({confidence.item() * 100:.2f}%)", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

    # Dibujar un rectángulo alrededor de la región detectada
    # Aquí, estamos dibujando un rectángulo fijo para la visualización.
    # Si tuvieses una red de detección de objetos, podrías usar las coordenadas del objeto detectado.
    height, width, _ = frame.shape
    cv2.rectangle(frame, (50, 50), (width-50, height-50), (0, 255, 0), 2)

    # Mostrar el video con la predicción
    cv2.imshow("Clasificación de Desechos", frame)

    # Salir presionando la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
