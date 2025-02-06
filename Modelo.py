import face_recognition
import os
import pickle
import numpy as np
from sklearn.svm import SVC

# Crear listas para los embeddings y los nombres
imagenes = []
nombres = []

# Recorre las carpetas dentro de 'dataset' (cada carpeta es una persona)
for carpeta in os.listdir("dataset"):
    if os.path.isdir(f"dataset/{carpeta}"):  # Si es una carpeta (persona)
        for archivo in os.listdir(f"dataset/{carpeta}"):
            if archivo.endswith(".jpg"):  # Solo procesamos imágenes .jpg
                imagen_path = os.path.join(f"dataset/{carpeta}", archivo)
                imagen = face_recognition.load_image_file(imagen_path)  # Cargar imagen
                try:
                    # Intentar extraer el embedding
                    embedding = face_recognition.face_encodings(imagen)[0]  # Obtener embedding del rostro
                    imagenes.append(embedding)  # Guardar el embedding
                    nombres.append(carpeta)  # Guardar el nombre de la persona (nombre de la carpeta)
                except IndexError:
                    print(f"Rostro no encontrado en {imagen_path}, omitiendo imagen.")
                    continue

# Entrenar el clasificador SVM
clf = SVC(gamma='scale')
clf.fit(imagenes, nombres)

# Guardar el modelo entrenado en un archivo .pkl
with open("modelo_svm.pkl", "wb") as archivo_svm:
    pickle.dump(clf, archivo_svm)

print("Modelo entrenado y guardado como modelo_svm.pkl")
