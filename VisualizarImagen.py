import cv2
import pickle
import face_recognition
from scipy.spatial import distance
from imutils import face_utils
import dlib
import imutils

# ======== Inicialización de Modelos ========

# Cargar el modelo de reconocimiento facial (SVM)
with open("Modelos/modelo_svm.pkl", "rb") as archivo_svm:
    clf = pickle.load(archivo_svm)

# Detector de rostros y predicción de landmarks faciales con dlib
detect = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("Modelos/shape_predictor_68_face_landmarks.dat")

# Índices de los landmarks para los ojos
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

# Parámetros para la detección de somnolencia
thresh = 0.25            # Umbral para el EAR
frame_check = 20          # Frames continuos para activar la alerta
contador_somnolencia = 0  # Contador de frames con somnolencia

# ======== Función para Calcular el EAR (Eye Aspect Ratio) ========

def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

# ======== Captura de Video ========

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = imutils.resize(frame, width=600)  # Redimensionar para mejor rendimiento
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detección de rostros para el reconocimiento facial
    caras = face_recognition.face_locations(rgb_frame)
    embeddings = face_recognition.face_encodings(rgb_frame, caras)

    # Detección de rostros para la somnolencia con dlib
    subjects = detect(gray, 0)

    for (top, right, bottom, left), embedding in zip(caras, embeddings):
        # Reconocimiento facial
        prediccion = clf.predict([embedding])[0]

        # Detección de somnolencia
        rect = dlib.rectangle(left, top, right, bottom)
        shape = predict(gray, rect)
        shape = face_utils.shape_to_np(shape)

        # Extraer los ojos
        leftEye = shape[lStart:lEnd]
        rightEye = shape[rStart:rEnd]
        leftEAR = eye_aspect_ratio(leftEye)
        rightEAR = eye_aspect_ratio(rightEye)
        ear = (leftEAR + rightEAR) / 2.0

        # Dibujar contornos de los ojos
        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

        # Mostrar el nombre de la persona
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, f"{prediccion}", (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Verificar somnolencia si el EAR está por debajo del umbral
        if ear < thresh:
            contador_somnolencia += 5 #Modificar el umbral de somnolencia | 5 Es mucho
            if contador_somnolencia >= frame_check:
                # Dibujar alerta en pantalla
                cv2.putText(frame, "!ALERTA DE SOMNOLENCIA!", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                cv2.rectangle(frame, (40, 20), (560, 70), (0, 0, 255), 2)
        else:
            contador_somnolencia = 0

    # Mostrar el video con resultados
    cv2.imshow("Reconocimiento Facial + Detección de Somnolencia", frame)

    # Salir presionando la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
