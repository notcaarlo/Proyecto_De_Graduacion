import cv2
import torch
import face_recognition
import numpy as np
from torchvision import transforms
from PIL import Image
import torch.nn as nn
import os
import torchvision.models as models

# Definir el modelo CNN + LSTM (el mismo que entrenamos antes)
class CNN_LSTM_Model(nn.Module):
    def __init__(self, lstm_input_size=512, hidden_size=64, num_layers=2, num_classes=2):
        super(CNN_LSTM_Model, self).__init__()
        
        # Cargar ResNet preentrenado (sin la capa final)
        self.resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.resnet = nn.Sequential(*list(self.resnet.children())[:-1])  # Quitamos la capa final de clasificación
        
        # LSTM para procesar secuencias de características
        self.lstm = nn.LSTM(lstm_input_size, hidden_size, num_layers, batch_first=True)

        # Capa final de clasificación (2 clases: Somnoliento / No somnoliento)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        batch_size, seq_len = x.size(0), x.size(1)
        
        # Extraemos las características de cada imagen usando ResNet
        resnet_features = []
        for t in range(seq_len):
            resnet_out = self.resnet(x[:, t, :, :, :])  # Extraemos características de cada imagen de la secuencia
            resnet_features.append(resnet_out.view(batch_size, -1))  # Aplanamos el output de ResNet
            
        resnet_features = torch.stack(resnet_features, dim=1)  # Forma la secuencia de características

        # Pasamos las características por el LSTM
        lstm_out, _ = self.lstm(resnet_features)  # [batch, seq_len, features]
        
        # Usamos la última salida del LSTM para la clasificación
        final_out = lstm_out[:, -1, :]
        
        # Clasificación final
        out = self.fc(final_out)
        
        return out

# Cargar el modelo de somnolencia entrenado
model_path = 'Modelos/cnn_lstm_model.pth'
model = CNN_LSTM_Model(lstm_input_size=512, hidden_size=64, num_layers=2, num_classes=2)
model.load_state_dict(torch.load(model_path))
model.eval()

# Función para predecir somnolencia usando el modelo
def predict_drowsiness(sequence):
    with torch.no_grad():
        inputs = torch.stack(sequence).unsqueeze(0)  # Añadir dimensión batch
        outputs = model(inputs)
        _, predicted = torch.max(outputs, 1)
        return "Somnoliento" if predicted == 1 else "No Somnoliento"

# Configuración de las transformaciones para las imágenes
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Configuración de OpenCV para la captura en tiempo real
cap = cv2.VideoCapture(0)
frame_sequence = []  # Secuencia de imágenes para somnolencia (10 imágenes)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convertir el frame a RGB (face_recognition requiere este formato)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detectar rostros en el frame usando face_recognition
    faces = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, faces)

    # Procesar cada cara detectada
    for (top, right, bottom, left), face_encoding in zip(faces, face_encodings):
        # Dibujar un rectángulo alrededor de la cara
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        # Reconocimiento de la persona (comparar el encoding de la cara)
        # Cargar las imágenes de entrenamiento previamente guardadas
        # Este es un ejemplo, se puede mejorar con un clasificador más robusto
        known_face_encodings = np.load('data/caras/embeddings.npy')
        distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        
        if len(distances) > 0 and min(distances) < 0.6:  # Si la cara es reconocida
            name = 'Desconocido'
            idx = np.argmin(distances)
            name = f'Persona {idx + 1}'  # Nombre o índice de la persona
            cv2.putText(frame, f"Persona: {name}", (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        
        # Mostrar la predicción de somnolencia
        face_image = frame[top:bottom, left:right]
        face_image = Image.fromarray(face_image).convert('RGB')
        face_tensor = transform(face_image).unsqueeze(0)
        
        # Añadir la imagen a la secuencia para predecir somnolencia
        frame_sequence.append(face_tensor)
        if len(frame_sequence) > 10:  # Mantener solo las últimas 10 imágenes
            frame_sequence.pop(0)

        if len(frame_sequence) == 10:
            drowsiness_status = predict_drowsiness(frame_sequence)
            cv2.putText(frame, f"Somnolencia: {drowsiness_status}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

    # Mostrar el frame con las predicciones
    cv2.imshow("Detección de Somnolencia y Reconocimiento Facial", frame)

    # Salir si presionamos 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar la cámara y cerrar las ventanas de OpenCV
cap.release()
cv2.destroyAllWindows()
