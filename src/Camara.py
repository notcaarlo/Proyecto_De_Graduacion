import cv2
import os
import face_recognition
import numpy as np

# Pide el nombre antes de comenzar la captura del video
nombre = input("Ingrese su nombre: ")
carpeta = f"../data/caras/{nombre}"  # Ruta 

# Verifica si la carpeta existe, si no la crea
if not os.path.exists(carpeta):
    os.makedirs(carpeta)

# Inicia la captura del video
cap = cv2.VideoCapture(0)
contador = 0

# Captura 50 imágenes
while contador < 50:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Detectar rostro
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    caras = face_recognition.face_locations(rgb_frame)

    # Procesar cada cara detectada
    for (top, right, bottom, left) in caras:
        rostro = rgb_frame[top:bottom, left:right]
        contador += 1
        # Guardar la imagen en la ruta deseada
        cv2.imwrite(f"{carpeta}/{contador}.jpg", rostro)

        # Dibujar un rectángulo alrededor de la cara detectada
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

    # Mostrar el frame con las caras detectadas
    cv2.imshow("Capturando Rostros", frame)

    # Si presionas 'q' se detendrá la captura
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
