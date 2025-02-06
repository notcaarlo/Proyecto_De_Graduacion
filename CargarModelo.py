import face_recognition
import os
import pickle
import numpy as np
from sklearn.svm import SVC

# Cargar modelo existente y lista de carpetas entrenadas si existen
try:
    with open("Modelos/modelo_svm.pkl", "rb") as archivo_svm:
        clf = pickle.load(archivo_svm)
    with open("Modelos/entrenados.pkl", "rb") as archivo_entrenados:
        carpetas_entrenadas = pickle.load(archivo_entrenados)
except FileNotFoundError:
    clf = SVC(gamma='scale', probability=True)
    carpetas_entrenadas = []

# Crear listas para los nuevos embeddings y nombres
imagenes = []
nombres = []

# Recorre las carpetas dentro de 'dataset' que aún no han sido entrenadas
for carpeta in os.listdir("dataset"):
    if os.path.isdir(f"dataset/{carpeta}") and carpeta not in carpetas_entrenadas:
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
                    continue
        carpetas_entrenadas.append(carpeta)  # Marcar carpeta como entrenada

# Solo actualizar el modelo si hay nuevas imágenes
if imagenes:
    clf.fit(imagenes, nombres)

    # Guardar el modelo y la lista de carpetas entrenadas
    with open("Modelos/modelo_svm.pkl", "wb") as archivo_svm:
        pickle.dump(clf, archivo_svm)

    with open("Modelos/entrenados.pkl", "wb") as archivo_entrenados:
        pickle.dump(carpetas_entrenadas, archivo_entrenados)

    print("Modelo actualizado y guardado como modelo_svm.pkl")
else:
    print("No hay nuevas carpetas para entrenar.")
