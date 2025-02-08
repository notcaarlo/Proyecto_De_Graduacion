import cv2
import os
import face_recognition
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# Pide el nombre antes de comenzar la captura del video
nombre = input("Ingrese su nombre: ")
carpeta = f"../data/caras/{nombre}"  # Ruta donde se guardarán las imágenes

# Verifica si la carpeta existe, si no la crea
if not os.path.exists(carpeta):
    os.makedirs(carpeta)

# Crear las subcarpetas train y val
train_folder = os.path.join(carpeta, 'train')
val_folder = os.path.join(carpeta, 'val')

if not os.path.exists(train_folder):
    os.makedirs(train_folder)
if not os.path.exists(val_folder):
    os.makedirs(val_folder)

# Inicia la captura del video desde la cámara
cap = cv2.VideoCapture(0)
contador = 0
embeddings = []  # Lista para almacenar los embeddings

# Cargar modelo ResNet preentrenado para extraer características
resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
resnet = nn.Sequential(*list(resnet.children())[:-1])  # Quitamos la capa final de clasificación
resnet.eval()

# Transformaciones para las imágenes
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Función para extraer características con ResNet
def extract_resnet_features(face_image):
    face_pil = Image.fromarray(face_image).convert('RGB')
    face_tensor = transform(face_pil).unsqueeze(0)  # Convertimos a tensor
    with torch.no_grad():
        features = resnet(face_tensor)
    return features.flatten().numpy()  # Aplanamos las características

# Captura de 50 imágenes
while contador < 50:  # Capturamos 50 imágenes
    ret, frame = cap.read()
    if not ret:
        break
    
    # Convertir el frame a RGB (face_recognition requiere este formato)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detectar rostros en el frame
    caras = face_recognition.face_locations(rgb_frame)

    # Procesar cada cara detectada
    for (top, right, bottom, left) in caras:
        rostro = rgb_frame[top:bottom, left:right]

        # Extraer características usando ResNet
        features = extract_resnet_features(rostro)
        embeddings.append(features)  # Añadir el embedding a la lista
        contador += 1

        # Determinar si la imagen va a train o val (25 imágenes para cada uno)
        if contador <= 25:
            save_path = os.path.join(train_folder, f"{contador}.jpg")
        else:
            save_path = os.path.join(val_folder, f"{contador - 25}.jpg")

        # Guardar la imagen del rostro en la ruta deseada
        cv2.imwrite(save_path, rostro)

        # Dibujar un rectángulo alrededor de la cara detectada
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        # Mostrar la cantidad de rostros capturados
        cv2.putText(frame, f"Rostros capturados: {contador}/50", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

    # Mostrar el frame con las caras detectadas
    cv2.imshow("Capturando Rostros", frame)

    # Si presionas 'q', se detendrá la captura
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar la captura y cerrar la ventana de OpenCV
cap.release()
cv2.destroyAllWindows()

# Guardar los embeddings en un archivo
embeddings = np.array(embeddings)
np.save(f"{carpeta}/embeddings.npy", embeddings)

print(f"Se han capturado {contador} rostros y se han guardado en las carpetas: {train_folder} y {val_folder}")
