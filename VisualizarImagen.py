import cv2
import pickle
import face_recognition

# Cargar el modelo entrenado
with open("modelo_svm.pkl", "rb") as archivo_svm:
    clf = pickle.load(archivo_svm)

# Iniciar la captura de video
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detectar rostros en el video
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    caras = face_recognition.face_locations(rgb_frame)
    embeddings = face_recognition.face_encodings(rgb_frame, caras)

    for (top, right, bottom, left), embedding in zip(caras, embeddings):
        # Usar el modelo SVM para hacer una predicción
        prediccion = clf.predict([embedding])[0]
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, f"{prediccion}", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    cv2.imshow("Reconocimiento Facial", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
