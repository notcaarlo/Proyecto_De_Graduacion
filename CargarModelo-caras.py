import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torchvision import models, transforms
from PIL import Image
import numpy as np
import face_recognition

# Crear listas para los embeddings y los nombres
imagenes = []
nombres = []

# Ruta base donde se almacenan las imágenes
base_path = os.path.join(os.path.dirname(__file__), 'data', 'caras')

# Verifica si la ruta de la base existe
if not os.path.exists(base_path):
    raise ValueError(f"La carpeta {base_path} no existe. Verifica la ruta.")

# Cargar el modelo ResNet18 preentrenado
from torchvision.models import ResNet18_Weights
resnet = models.resnet18(weights=ResNet18_Weights.DEFAULT)  # Usamos ResNet18 de PyTorch
resnet.eval()  # Configuramos el modelo en modo de evaluación

# Eliminar la capa final de clasificación en ResNet
resnet = nn.Sequential(*list(resnet.children())[:-1])

# Definir las transformaciones para las imágenes
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize((224, 224)),  # Redimensionar a 224x224
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # Normalizar
])

# Recorre las carpetas dentro de 'data/caras' (cada carpeta es una persona)
for carpeta in os.listdir(base_path):
    carpeta_path = os.path.join(base_path, carpeta)
    
    # Verifica que sea un directorio (carpeta de una persona)
    if os.path.isdir(carpeta_path):
        # Recorre las imágenes dentro de cada carpeta
        for archivo in os.listdir(carpeta_path):
            if archivo.endswith(".jpg"):
                imagen_path = os.path.join(carpeta_path, archivo)
                imagen = face_recognition.load_image_file(imagen_path)
                
                try:
                    # Obtener el rostro y redimensionarlo para el modelo ResNet18
                    rostro = imagen
                    rostro_resized = Image.fromarray(rostro)  # Convertir a imagen PIL
                    rostro_resized = transform(rostro_resized).unsqueeze(0)  # Aplicar transformaciones y agregar batch dimension

                    # Extraer características con el modelo ResNet18
                    with torch.no_grad():  # Desactivar el cálculo de gradientes para ahorrar memoria
                        features = resnet(rostro_resized)  # Pasar la imagen a través de ResNet18
                    imagenes.append(features.flatten().numpy())  # Aplanar las características y agregar a la lista
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

# Asegurarse de que X_tensor tenga la forma [batch_size, seq_len, input_size]
X_tensor = X_tensor.view(X_tensor.size(0), 1, 512)  # Redimensiona para que coincida con input_size

# Verifica la forma de X_tensor antes de pasarlo al LSTM
print("Forma de X_tensor antes de pasarlo al LSTM:", X_tensor.shape)  # Debería ser [batch_size, 1, 512]

# Crear DataLoader
dataset = TensorDataset(X_tensor, y_tensor)
train_loader = DataLoader(dataset, batch_size=32, shuffle=True)

# Definir la red neuronal con CNN + LSTM
class FaceRecognitionCNNLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, num_classes):
        super(FaceRecognitionCNNLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc1 = nn.Linear(hidden_size, 128)
        self.fc2 = nn.Linear(128, num_classes)
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        out, (hn, cn) = self.lstm(x)
        if out.dim() == 3:
            out = out[:, -1, :]  # Último paso de la secuencia
        out = self.dropout(out)
        out = torch.relu(self.fc1(out))
        out = self.fc2(out)
        return out


# Definir el modelo
input_size = 512  # Características extraídas por ResNet
hidden_size = 128
num_layers = 2
num_classes = len(y_labels)

model = FaceRecognitionCNNLSTM(input_size, hidden_size, num_layers, num_classes)

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
model_save_path = os.path.join(os.path.dirname(__file__), 'Modelos', 'modelo_cnn_lstm.pth')
labels_save_path = os.path.join(os.path.dirname(__file__), 'Modelos', 'labels.txt')

# Verificar si la carpeta existe antes de guardar
if not os.path.exists(os.path.dirname(model_save_path)):
    os.makedirs(os.path.dirname(model_save_path))

torch.save(model.state_dict(), model_save_path)

with open(labels_save_path, "w") as f:
    for label in y_labels:
        f.write(f"{label}\n")

print(f"Modelo entrenado y guardado en {model_save_path}.")
