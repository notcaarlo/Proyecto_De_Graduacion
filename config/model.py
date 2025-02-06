# src/model.py

from torchvision import models
import torch.nn as nn
from config.config import Config

def get_model(num_classes):
    if Config.MODEL == 'resnet18':
        model = models.resnet18(pretrained=True)
    elif Config.MODEL == 'resnet34':
        model = models.resnet34(pretrained=True)
    elif Config.MODEL == 'resnet50':
        model = models.resnet50(weights="IMAGENET1K_V1")
    else:
        raise ValueError("Modelo no soportado")

    # Reemplazar la última capa para ajustarse a nuestro dataset
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, num_classes)

    return model
