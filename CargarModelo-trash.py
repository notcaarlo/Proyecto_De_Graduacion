import torch
import torch.nn as nn
from torchvision import models, transforms
from torch.optim import Adam
from torch.utils.data import DataLoader
from config.dataset import get_data_loaders
from config.config import Config
import time

# Configuración del dispositivo
device = torch.device("cuda" if torch.cuda.is_available() and Config.USE_GPU else "cpu")

# Cargar el modelo ResNet18 preentrenado
model_ft = models.resnet18(weights="IMAGENET1K_V1")

# Congelar todas las capas iniciales
for param in model_ft.parameters():
    param.requires_grad = False

# Cambiar la capa final para que se ajuste a tu número de clases (6 clases para los desechos)
num_ftrs = model_ft.fc.in_features
model_ft.fc = nn.Linear(num_ftrs, 6)  # Asumiendo 6 clases de desechos
model_ft = model_ft.to(device)

# Definir el criterio de pérdida y el optimizador
criterion = nn.CrossEntropyLoss()
optimizer = Adam(model_ft.fc.parameters(), lr=Config.LEARNING_RATE)  # Solo optimizar las capas finales

# Cargar los datos (asumiendo que ya tienes esta función configurada)
data_dir = 'data/dataset-trash'  # Cambia esto a tu ruta de datos
dataloaders, dataset_sizes = get_data_loaders(data_dir)

# Entrenamiento del modelo con Fine-Tuning
def train_model(model, criterion, optimizer, dataloaders, dataset_sizes, num_epochs=25):
    since = time.time()
    best_model_wts = model.state_dict()
    best_acc = 0.0

    for epoch in range(num_epochs):
        print(f'Epoch {epoch + 1}/{num_epochs}')
        print('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                if phase == 'train':
                    loss.backward()
                    optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = model.state_dict()

        print()

    time_elapsed = time.time() - since
    print(f'Training complete in {time_elapsed // 60}m {time_elapsed % 60}s')
    print(f'Best val Acc: {best_acc:.4f}')

    model.load_state_dict(best_model_wts)
    return model

# Entrenamos el modelo con fine-tuning
model_ft = train_model(model_ft, criterion, optimizer, dataloaders, dataset_sizes, num_epochs=Config.EPOCHS)

# Guardar el modelo entrenado
torch.save(model_ft.state_dict(), 'modelos/modelo_resnet_finetuned.pth')
