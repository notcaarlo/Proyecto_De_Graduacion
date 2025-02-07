import cv2
import os
import face_recognition
import numpy as np

# Pide el nombre antes de comenzar la captura del video
nombre = input("Ingrese su nombre: ")
carpeta = f"../data/caras/{nombre}"  # Ruta donde se guardarán las imágenes

# Verifica si la carpeta existe, si no la crea
if not os.path.exists(carpeta):
    os.makedirs(carpeta)

# Inicia la captura del video desde la cámara
cap = cv2.VideoCapture(0)
contador = 0
embeddings = []  # Lista para almacenar los embeddings

# Captura de 50 imágenes
while contador < 50:  # Capturamos 50 imágenes
    ret, frame = cap.read()
    if not ret:
        break
    
    # Convertir el frame a RGB (face_recognition requiere este formato)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detectar rostros en el frame
    caras = face_recognition.face_locations(rgb_frame)

    # Procesar cada cara detectada
    for (top, right, bottom, left) in caras:
        rostro = rgb_frame[top:bottom, left:right]

        # Obtener el embedding del rostro
        encoding = face_recognition.face_encodings(rgb_frame, [(top, right, bottom, left)])

        if encoding:
            embeddings.append(encoding[0])  # Añadir el embedding a la lista
            contador += 1

            # Guardar la imagen del rostro en la ruta deseada
            cv2.imwrite(f"{carpeta}/{contador}.jpg", rostro)

            # Dibujar un rectángulo alrededor de la cara detectada
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            # Mostrar la cantidad de rostros capturados
            cv2.putText(frame, f"Rostros capturados: {contador}/50", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

    # Mostrar el frame con las caras detectadas
    cv2.imshow("Capturando Rostros", frame)

    # Si presionas 'q', se detendrá la captura
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar la captura y cerrar la ventana de OpenCV
cap.release()
cv2.destroyAllWindows()

# Guardar los embeddings en un archivo
embeddings = np.array(embeddings)
np.save(f"{carpeta}/embeddings.npy", embeddings)

print(f"Se han capturado {contador} rostros y se han guardado en la carpeta: {carpeta}")
