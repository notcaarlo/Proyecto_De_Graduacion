# src/config.py

class Config:
    BATCH_SIZE = 8
    EPOCHS = 10
    LEARNING_RATE = 0.001
    IMAGE_SIZE = (224, 224)  # Redimensionar las imágenes a 224x224
    USE_GPU = False          # Si hay una GPU disponible
    MODEL = 'resnet18'       # Modelo a usar (resnet18, resnet34, etc.)
