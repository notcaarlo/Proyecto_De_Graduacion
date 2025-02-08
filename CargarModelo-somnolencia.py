import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from sklearn.preprocessing import LabelEncoder
from PIL import Image
import numpy as np

# Definir el modelo CNN + LSTM
class CNN_LSTM_Model(nn.Module):
    def __init__(self, lstm_input_size=512, hidden_size=64, num_layers=2, num_classes=2):
        super(CNN_LSTM_Model, self).__init__()
        
        # Cargar ResNet preentrenado (sin la capa final)
        self.resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.resnet.conv1 = nn.Conv2d(1, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False)  # Cambiar la primera capa para aceptar imágenes en escala de grises
        self.resnet = nn.Sequential(*list(self.resnet.children())[:-1])  # Quitamos la capa final de clasificación
        
        # LSTM para procesar secuencias de características
        self.lstm = nn.LSTM(lstm_input_size, hidden_size, num_layers, batch_first=True)

        # Capa final de clasificación (2 clases: Somnoliento / No somnoliento)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x es ahora una secuencia de imágenes [batch_size, seq_len, 1, 224, 224]
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

# Dataset personalizado para cargar las secuencias de imágenes
class DrowsinessDataset(Dataset):
    def __init__(self, base_path, transform=None, sequence_length=56, num_sequences=5):
        self.base_path = base_path
        self.transform = transform
        self.sequence_length = sequence_length
        self.num_sequences = num_sequences
        self.data = []
        self.labels = []
        
        # Carpetas de "abiertos" y "cerrados"
        for label, folder in enumerate(['abiertos', 'cerrados']):
            folder_path = os.path.join(base_path, folder)
            if not os.path.exists(folder_path):
                continue
            images = sorted(os.listdir(folder_path))
            if not images:
                continue
            
            # Dividir las imágenes en secuencias
            for i in range(0, len(images), self.sequence_length):
                # Obtener una secuencia de imágenes
                seq_images = images[i:i + self.sequence_length]
                
                if len(seq_images) == self.sequence_length:
                    seq_images_paths = [os.path.join(folder_path, img) for img in seq_images]
                    
                    # Leer y aplicar transformaciones
                    seq_images_tensor = []
                    for img_path in seq_images_paths:
                        try:
                            img = Image.open(img_path).convert('L')  # Convertir a escala de grises
                            if self.transform:
                                img = self.transform(img)
                            seq_images_tensor.append(img)
                        except Exception as e:
                            print(f"Error al cargar la imagen {img_path}: {e}")
                    
                    # Agregar la secuencia y la etiqueta
                    if len(seq_images_tensor) == self.sequence_length:
                        self.data.append(torch.stack(seq_images_tensor))
                        self.labels.append(label)  # 0 para "Open_Eyes", 1 para "Closed_Eyes"

        # Codificar las etiquetas
        if self.labels:
            self.label_encoder = LabelEncoder()
            self.labels = self.label_encoder.fit_transform(self.labels)
        
        print(f"Total de secuencias cargadas: {len(self.data)}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx], torch.tensor(self.labels[idx], dtype=torch.long)

# Configuración de transformaciones
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5], std=[0.5])  # Normalización para imágenes en escala de grises
])

# Cargar el dataset
base_path = 'data/somnolencia'  # Ruta relativa donde están las imágenes
dataset = DrowsinessDataset(base_path, transform=transform, sequence_length=56, num_sequences=5)
train_loader = DataLoader(dataset, batch_size=32, shuffle=True)

# Instanciar el modelo
model = CNN_LSTM_Model(lstm_input_size=512, hidden_size=64, num_layers=2, num_classes=2)

# Definir el optimizador y la función de pérdida
criterion = nn.CrossEntropyLoss()  # Para clasificación binaria
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# Función de entrenamiento
def train_model(model, train_loader, num_epochs=10):
    model.train()  # Entrenamos el modelo
    for epoch in range(num_epochs):
        running_loss = 0.0
        correct_predictions = 0
        total_predictions = 0
        
        for inputs, labels in train_loader:
            # Entrenamiento
            optimizer.zero_grad()
            
            # Pasamos las secuencias de imágenes por el modelo
            outputs = model(inputs)
            
            # Calcular la pérdida
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            # Estadísticas
            running_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            correct_predictions += (predicted == labels).sum().item()
            total_predictions += labels.size(0)
        
        accuracy = correct_predictions / total_predictions * 100
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {running_loss / len(train_loader)}, Accuracy: {accuracy}%")
        
    print("Entrenamiento completado.")

# Entrenar el modelo
train_model(model, train_loader, num_epochs=10)

# Crear la carpeta 'Modelos' si no existe
os.makedirs('Modelos', exist_ok=True)

# Guardar el modelo entrenado
print("Guardando el modelo...")
torch.save(model.state_dict(), 'Modelos/somnolencia.pth')
print("Modelo entrenado y guardado con éxito.")