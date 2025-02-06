import face_recognition
import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Crear listas para los embeddings y los nombres
imagenes = []
nombres = []

# Recorre las carpetas dentro de 'dataset' (cada carpeta es una persona)
for carpeta in os.listdir("dataset"):
    if os.path.isdir(f"dataset/{carpeta}"):
        for archivo in os.listdir(f"dataset/{carpeta}"):
            if archivo.endswith(".jpg"):
                imagen_path = os.path.join(f"dataset/{carpeta}", archivo)
                imagen = face_recognition.load_image_file(imagen_path)
                try:
                    embedding = face_recognition.face_encodings(imagen)[0]
                    imagenes.append(embedding)
                    nombres.append(carpeta)
                except IndexError:
                    print(f"Rostro no encontrado en {imagen_path}, omitiendo imagen.")

# Convertir listas a arrays de NumPy
X = np.array(imagenes)
y_labels = list(set(nombres))
y = np.array([y_labels.index(name) for name in nombres])

# Convertir a tensores de PyTorch
X_tensor = torch.tensor(X, dtype=torch.float32)
y_tensor = torch.tensor(y, dtype=torch.long)

# Crear DataLoader
dataset = TensorDataset(X_tensor, y_tensor)
train_loader = DataLoader(dataset, batch_size=32, shuffle=True)

# Definir la red neuronal
class FaceRecognitionNN(nn.Module):
    def __init__(self):
        super(FaceRecognitionNN, self).__init__()
        self.fc1 = nn.Linear(128, 256)  # Entrada de 128 (embedding de cara) a 256
        self.dropout1 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(256, 128)  # Capa intermedia de 256 a 128
        self.dropout2 = nn.Dropout(0.5)
        self.fc3 = nn.Linear(128, len(y_labels))  # Capa de salida con número de clases

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout1(x)
        x = torch.relu(self.fc2(x))
        x = self.dropout2(x)
        x = self.fc3(x)
        return x

# Instanciar el modelo
model = FaceRecognitionNN()

# Definir el optimizador y la función de pérdida
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

# Entrenar el modelo
epochs = 20
for epoch in range(epochs):
    model.train()  # Configurar el modelo en modo de entrenamiento
    running_loss = 0.0
    correct = 0
    total = 0
    
    for data, target in train_loader:
        optimizer.zero_grad()  # Limpiar los gradientes
        output = model(data)   # Realizar la predicción
        loss = criterion(output, target)  # Calcular la pérdida
        loss.backward()  # Hacer backpropagation
        optimizer.step()  # Actualizar los pesos
        
        running_loss += loss.item()
        _, predicted = torch.max(output, 1)  # Obtener la clase predicha
        total += target.size(0)
        correct += (predicted == target).sum().item()
    
    # Calcular y mostrar la precisión y pérdida por época
    accuracy = 100 * correct / total
    print(f"Epoch [{epoch+1}/{epochs}], Loss: {running_loss/len(train_loader):.4f}, Accuracy: {accuracy:.2f}%")

# Guardar el modelo y las etiquetas
torch.save(model.state_dict(), "Modelos/modelo_cnn.pth")
with open("Modelos/labels.txt", "w") as f:
    for label in y_labels:
        f.write(f"{label}\n")

print("Modelo entrenado y guardado.")
