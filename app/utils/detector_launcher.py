# app/utils/detector_launcher.py
import os
import threading
import time
import requests
import cv2 # Importante para procesar la imagen
import numpy as np # Importante para el frame vacío

# =========================================================
# === INICIO: CLASE PARA STREAMING (BÚFER SEGURO) ===
# =========================================================
class StreamingCamera:
    """
    Un búfer de cámara seguro para hilos (thread-safe).
    El hilo del detector escribe frames aquí, y el hilo de Flask lee desde aquí.
    """
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()
        # Crear un frame negro inicial y guardar una copia
        self.placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(self.placeholder_frame, "Iniciando Camara...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        self._reset_placeholder = self.placeholder_frame.copy()

    def set_frame(self, frame: np.ndarray):
        """Llamado por el hilo del detector para guardar el último frame."""
        with self.lock:
            self.frame = frame.copy()

    def get_frame_bytes(self) -> bytes:
        """Llamado por el hilo de Flask para enviar el frame al navegador."""
        with self.lock:
            if self.frame is None:
                frame_to_encode = self.placeholder_frame
            else:
                frame_to_encode = self.frame
        
        (flag, encoded_image) = cv2.imencode(".jpg", frame_to_encode)
        if not flag:
            return b''
            
        return encoded_image.tobytes()

    def reset(self):
        """Resetea el búfer para una nueva sesión."""
        with self.lock:
            self.frame = None
            # Restaura el placeholder al texto "Iniciando Camara..."
            self.placeholder_frame = self._reset_placeholder.copy()

# --- Instancia global del búfer de la cámara (se crea UNA SOLA VEZ) ---
camera_buffer = StreamingCamera()
# =========================================================
# === FIN: CLASE PARA STREAMING ===
# =========================================================


# Variables globales de control (sin cambios)
_stop_flag = threading.Event()
_detector_thread = None


# =========================================================
# === FUNCIÓN _post_alerta (Para Somnolencia) ===
# =========================================================
def _post_alerta(server: str, id_usuario: int, id_vehiculo: int, duracion: float, frame):
    """
    Envía una alerta de SOMNOLENCIA al backend.
    """
    url = f"{server.rstrip('/')}/api/alertas"
    
    def nivel_por_duracion(seg: float) -> str:
        if seg <= 5.0:      # 1.5s a 5.0s
            return "bajo"
        elif seg <= 11.0:     # 5.1s a 11.0s
            return "medio"
        else:               # > 11.0s (12s para adelante)
            return "critico"

    nivel = nivel_por_duracion(duracion)
    data = {
        "id_usuario": str(id_usuario), "id_vehiculo": str(id_vehiculo),
        "duracion": str(round(duracion, 2)), "nota": "Alerta automática del detector",
        "nivel_somnolencia": nivel
    }
    files = None
    if frame is not None and nivel == "critico":
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            files = {'evidencia_img': ('evidencia.jpg', frame_bytes, 'image/jpeg')}
            print("[API] Alerta CRÍTICA (Somnolencia). Adjuntando imagen.")
        except Exception as e:
            print(f"[API] Error al codificar la imagen: {e}")
    elif frame is not None:
        print("[API] Alerta BAJO/MEDIO (Somnolencia). Foto descartada.")

    try:
        r = requests.post(url, data=data, files=files, timeout=5)
        if r.status_code >= 400:
            print(f"[API] ❌ Error {r.status_code}: {r.text}")
        else:
            print(f"[API] ✅ Alerta (Somnolencia) enviada: {data['nivel_somnolencia']} ({data['duracion']}s)")
    except requests.RequestException as e:
        print(f"[API] ⚠️ Error de red: {e}")

# =========================================================
# === INICIO: NUEVA FUNCIÓN (Para Obstrucción) ===
# =========================================================
def _post_obstruction_alerta(server: str, id_usuario: int, id_vehiculo: int, duracion: float, frame):
    """
    Envía una alerta de OBSTRUCCIÓN/ANTI-TAMPER al backend.
    Siempre se trata como crítica y siempre adjunta foto.
    """
    url = f"{server.rstrip('/')}/api/alertas"
    
    data = {
        "id_usuario": str(id_usuario),
        "id_vehiculo": str(id_vehiculo),
        "duracion": str(round(duracion, 2)),
        "nota": "ALERTA DE OBSTRUCCION: No se detecta rostro/camara tapada.",
        "nivel_somnolencia": "critico" # Las alertas de obstrucción siempre son críticas
    }

    files = None
    if frame is not None:
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            files = {'evidencia_img': ('obstruccion.jpg', frame_bytes, 'image/jpeg')}
            print("[API] Alerta CRÍTICA (Obstrucción). Adjuntando imagen.")
        except Exception as e:
            print(f"[API] Error al codificar la imagen de obstrucción: {e}")
    
    try:
        r = requests.post(url, data=data, files=files, timeout=5)
        if r.status_code >= 400:
            print(f"[API] ❌ Error {r.status_code}: {r.text}")
        else:
            print(f"[API] ✅ Alerta (Obstrucción) enviada.")
    except requests.RequestException as e:
        print(f"[API] ⚠️ Error de red: {e}")
# =========================================================
# === FIN: NUEVA FUNCIÓN ===
# =========================================================


# =========================================================
# === INICIO: BUCLE DE DETECCIÓN MODIFICADO ===
# =========================================================
def _detector_thread_func(id_usuario, id_vehiculo):
    """
    Hilo de ejecución del detector (modo headless).
    """
    global camera_buffer # Usa el búfer global
    try:
        from ia_module.mediapipe_detector import SomnolenceDetector, DetectorConfig
        import cv2
    except Exception as e:
        print(f"[Detector] Import lazy falló (mediapipe/cv2 no disponibles): {e}")
        return

    print(f"[Detector] Iniciando para usuario={id_usuario}, vehiculo={id_vehiculo}")
    
    cfg = DetectorConfig(
        calibration_seconds=6.0, threshold_ratio=0.75,
        min_close_seconds=1.5, draw_landmarks=False, 
    )
    detector = SomnolenceDetector(cfg)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[Detector] ❌ Error: no se pudo abrir la cámara.")
        return

    # --- Calibración ---
    try:
        print("[Calibración] Calibrando, por favor mira a la cámara...")
        detector.calibrate(cap) 
        print("[Detector] ✅ Cámara activa, monitoreo iniciado.")
    except RuntimeError as e:
        print(f"[Detector] Error en calibración: {e}")
        cap.release()
        return

    try:
        while not _stop_flag.is_set():
            ok, frame = cap.read()
            if not ok:
                print("[Detector] Fin de stream o error de cámara.")
                break
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = detector.face_mesh.process(frame_rgb)
            
            l_ear, r_ear = detector._calc_ears(frame, results)
            ear = (l_ear + r_ear) / 2.0 if l_ear and r_ear else None
            
            now = time.time()
            somnoliento = False # Para dibujar el overlay
            
            # --- Lógica de detección (Somnolencia vs Obstrucción) ---
            
            # (ear is None) significa que NO SE DETECTA ROSTRO
            if ear is None and detector.state.threshold_ear is not None:
                # --- INICIO: LÓGICA ANTI-TAMPER / OBSTRUCCIÓN ---
                if detector.state.no_face_start_ts is None:
                    # Iniciar temporizador de "sin rostro"
                    detector.state.no_face_start_ts = now
                
                elapsed_no_face = now - detector.state.no_face_start_ts
                
                # 1. Iniciar alarma local después de 3 segundos
                if elapsed_no_face > 3.0:
                    detector._start_beep()
                    somnoliento = True # Reutilizar para el overlay rojo
                    
                # 2. Enviar alerta de obstrucción después de 60 segundos
                OBSTRUCTION_THRESHOLD_SECONDS = 60.0
                if elapsed_no_face > OBSTRUCTION_THRESHOLD_SECONDS and detector.state.no_face_alert_sent is False:
                    print(f"[Detector] UMBRAL DE OBSTRUCCIÓN ({OBSTRUCTION_THRESHOLD_SECONDS}s) ALCANZADO. Enviando alerta...")
                    detector.state.no_face_alert_sent = True
                    # Tomar una foto (será negra o de la obstrucción)
                    frame_alerta = frame.copy() 
                    _post_obstruction_alerta("http://127.0.0.1:5000", id_usuario, id_vehiculo, elapsed_no_face, frame_alerta)
                
                # --- FIN: LÓGICA ANTI-TAMPER ---

            # (ear is not None) significa que SÍ SE DETECTA ROSTRO
            elif ear is not None and detector.state.threshold_ear is not None:
                # --- INICIO: LÓGICA DE SOMNOLENCIA (la que ya tenías) ---
                
                # 1. Resetear el temporizador de obstrucción
                if detector.state.no_face_start_ts is not None:
                    detector.state.no_face_start_ts = None
                    detector.state.no_face_alert_sent = False
                    detector._stop_beep() # Parar la alarma de obstrucción

                # 2. Lógica de somnolencia (ojos cerrados)
                if ear < detector.state.threshold_ear:
                    if detector.state.closed_start_ts is None:
                        detector.state.closed_start_ts = now
                else:
                    # Ojos abiertos: procesar alertas Bajas/Medias
                    if detector.state.closed_start_ts is not None:
                        duracion = now - detector.state.closed_start_ts
                        if duracion >= detector.cfg.min_close_seconds and detector.state.critical_alert_sent is False:
                            detector.state.last_alert_duration = duracion
                            detector.state.total_somnolencia_time += duracion
                        
                        detector.state.closed_start_ts = None
                        detector.state.critical_alert_sent = False
                        detector._stop_beep() 

                # 3. Lógica mientras los ojos ESTÁN CERRADOS (Somnolencia)
                if detector.state.closed_start_ts is not None:
                    elapsed_somnolencia = now - detector.state.closed_start_ts
                    
                    if elapsed_somnolencia >= detector.cfg.min_close_seconds:
                        somnoliento = True
                        detector._start_beep()
                        if detector.state.alert_start_frame is None:
                             detector.state.alert_start_frame = frame.copy()

                    # 4. Enviar alerta crítica (desmayo)
                    CRITICAL_THRESHOLD_SECONDS = 11.0
                    if elapsed_somnolencia > CRITICAL_THRESHOLD_SECONDS and detector.state.critical_alert_sent is False:
                        print(f"[Detector] UMBRAL CRÍTICO ({CRITICAL_THRESHOLD_SECONDS}s) ALCANZADO. Enviando alerta...")
                        detector.state.critical_alert_sent = True 
                        frame_alerta = detector.state.alert_start_frame
                        _post_alerta("http://127.0.0.1:5000", id_usuario, id_vehiculo, elapsed_somnolencia, frame_alerta)
                else:
                    # Este 'else' es solo si los ojos están abiertos
                    if detector.state.no_face_start_ts is None: # No parar el beep de obstrucción
                        detector._stop_beep()
                
                # --- FIN: LÓGICA DE SOMNOLENCIA ---
            
            else:
                # (Rostro detectado pero aún no calibrado, o se perdió)
                detector._stop_beep()


            # --- Enviar alertas Bajas/Medias (si las hay) ---
            alerta_result = detector.consume_alert_if_ready()
            if alerta_result:
                duracion, frame_alerta = alerta_result
                _post_alerta("http://127.0.0.1:5000", id_usuario, id_vehiculo, duracion, frame_alerta)

            # --- Lógica visual (Overlay para CUALQUIER alerta) ---
            if somnoliento:
                # Dibuja un borde rojo simple
                cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 10)
                
                # Texto de alerta (Somnolencia o Obstrucción)
                alert_text = "ALERTA SOMNOLENCIA"
                if detector.state.no_face_start_ts is not None:
                    alert_text = "ALERTA OBSTRUCCION"
                
                cv2.putText(frame, alert_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

            # --- Guardar el frame en el búfer para el streaming ---
            camera_buffer.set_frame(frame)
            
            # --- ELIMINADO: 'cv2.imshow' y 'cv2.waitKey' ---
            # (El hilo del detector ya no debe mostrar ventanas)
            
            time.sleep(0.02) # Controlar el bucle a ~50fps
            
    except Exception as e:
        print(f"[Detector] ⚠️ Error durante ejecución: {e}")
    finally:
        detector._stop_beep()
        cap.release()
        detector.face_mesh.close()
        # --- ELIMINADO: 'cv2.destroyAllWindows()' ---
        print("[Detector] 📴 Finalizado correctamente.")

# =========================================================
# === FUNCIONES iniciar_detector y detener_detector ===
# =========================================================
def iniciar_detector(id_usuario: int, id_vehiculo: int):
    global _detector_thread, _stop_flag, camera_buffer

    if os.getenv("APP_DISABLE_DETECTOR", "0") == "1":
        print("[Detector] Deshabilitado por APP_DISABLE_DETECTOR=1 (modo tests).")
        return

    if _detector_thread and _detector_thread.is_alive():
        print("[Detector] Ya hay un detector activo.")
        return

    # --- MODIFICADO: Solo resetear el búfer existente ---
    camera_buffer.reset() 
    
    _stop_flag.clear()
    _detector_thread = threading.Thread(
        target=_detector_thread_func, args=(id_usuario, id_vehiculo), daemon=True
    )
    _detector_thread.start()
    print("[Detector] 🚀 Hilo de monitoreo iniciado.")


def detener_detector():
    global _detector_thread, _stop_flag

    if os.getenv("APP_DISABLE_DETECTOR", "0") == "1":
        print("[Detector] Deshabilitado (modo tests). Nada que detener.")
        return

    if not _detector_thread or not _detector_thread.is_alive():
        print("[Detector] No hay detector activo.")
        return

    print("[Detector] 🛑 Señal de parada enviada.")
    _stop_flag.set()
    _detector_thread.join(timeout=5)