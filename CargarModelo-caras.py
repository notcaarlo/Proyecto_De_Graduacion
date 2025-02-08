import os
import numpy as np
import torch
import torch.nn as nn
import face_recognition
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from torchvision import models, transforms
from PIL import Image
import cv2

# Cargar el modelo FaceNet preentrenado para obtener embeddings
class FaceNet(nn.Module):
    def __init__(self):
        super(FaceNet, self).__init__()
        self.resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.resnet = nn.Sequential(*list(self.resnet.children())[:-1])  # Quitamos la capa final

    def forward(self, x):
        return self.resnet(x)

# Función para extraer los embeddings de las imágenes usando FaceNet
def extract_resnet_features(face_image, model, transform):
    face_pil = Image.fromarray(face_image).convert('RGB')
    face_tensor = transform(face_pil).unsqueeze(0)  # Convertimos a tensor
    with torch.no_grad():
        features = model(face_tensor)
    return features.flatten().numpy()  # Aplanamos las características

# Dataset personalizado para cargar las imágenes de los rostros
def create_dataset(base_path, transform, model):
    embeddings = []
    labels = []
    
    for person in os.listdir(base_path):
        person_path = os.path.join(base_path, person, 'train')
        if not os.path.isdir(person_path):
            continue
        for img_name in os.listdir(person_path):
            img_path = os.path.join(person_path, img_name)
            face_image = face_recognition.load_image_file(img_path)
            face_locations = face_recognition.face_locations(face_image)
            
            if len(face_locations) == 0:
                continue
            top, right, bottom, left = face_locations[0]
            face_image = face_image[top:bottom, left:right]
            
            # Extraer embeddings usando FaceNet
            features = extract_resnet_features(face_image, model, transform)
            embeddings.append(features)
            labels.append(person)
    
    return np.array(embeddings), np.array(labels)

# Cargar el modelo FaceNet
face_model = FaceNet()
face_model.eval()  # Ponemos el modelo en modo evaluación

# Transformaciones para las imágenes
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Ruta base donde están las imágenes de entrenamiento
base_path = 'data/caras'

# Crear el dataset de embeddings y etiquetas
embeddings, labels = create_dataset(base_path, transform, face_model)

# Codificar las etiquetas (nombres) como números
label_encoder = LabelEncoder()
labels = label_encoder.fit_transform(labels)

# Dividir el dataset en entrenamiento y validación
X_train, X_test, y_train, y_test = train_test_split(embeddings, labels, test_size=0.2, random_state=42)

# Entrenar el clasificador SVM
svm_clf = SVC(kernel='linear', probability=True)
svm_clf.fit(X_train, y_train)

# Evaluar el modelo
train_accuracy = svm_clf.score(X_train, y_train)
test_accuracy = svm_clf.score(X_test, y_test)

print(f'Accuracy en entrenamiento: {train_accuracy * 100:.2f}%')
print(f'Accuracy en validación: {test_accuracy * 100:.2f}%')

# Guardar el modelo SVM y el encoder de etiquetas
import joblib
joblib.dump(svm_clf, 'Modelos/svm_model.pkl')
joblib.dump(label_encoder, 'Modelos/label_encoder.pkl')

print("Modelo entrenado y guardado con éxito.")
