# app/utils/detector_launcher.py
import os
import threading
import time
import requests
import cv2
import numpy as np
class StreamingCamera:
    """
    Un búfer de cámara seguro para hilos (thread-safe).
    El hilo del detector escribe frames aquí, y el hilo de Flask lee desde aquí.
    """
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()
        self.placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
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
            self.placeholder_frame = self._reset_placeholder.copy()
            
camera_buffer = StreamingCamera()

# Variables globales de control
_stop_flag = threading.Event()
_detector_thread = None

# === FUNCIÓN PARA ENVIAR ALERTAS AL BACKEND ===
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
            print(f"[API] Error {r.status_code}: {r.text}")
        else:
            print(f"[API] Alerta (Somnolencia) enviada: {data['nivel_somnolencia']} ({data['duracion']}s)")
    except requests.RequestException as e:
        print(f"[API] Error de red: {e}")
        
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
        "nivel_somnolencia": "critico"
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
            print(f"[API] Error {r.status_code}: {r.text}")
        else:
            print(f"[API] Alerta (Obstrucción) enviada.")
    except requests.RequestException as e:
        print(f"[API] Error de red: {e}")

def _detector_thread_func(id_usuario, id_vehiculo):
    """
    Hilo de ejecución del detector (modo headless).
    """
    global camera_buffer
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
        print("[Detector] Error: no se pudo abrir la cámara.")
        return
    
    try:
        print("[Calibración] Calibrando, por favor mira a la cámara...")
        detector.calibrate(cap) 
        print("[Detector] Cámara activa, monitoreo iniciado.")
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
            somnoliento = False 
            
            if ear is None and detector.state.threshold_ear is not None:
                if detector.state.no_face_start_ts is None:
                    detector.state.no_face_start_ts = now
                
                elapsed_no_face = now - detector.state.no_face_start_ts
                
                if elapsed_no_face > 3.0:
                    detector._start_beep()
                    somnoliento = True
                    
                OBSTRUCTION_THRESHOLD_SECONDS = 60.0
                if elapsed_no_face > OBSTRUCTION_THRESHOLD_SECONDS and detector.state.no_face_alert_sent is False:
                    print(f"[Detector] UMBRAL DE OBSTRUCCIÓN ({OBSTRUCTION_THRESHOLD_SECONDS}s) ALCANZADO. Enviando alerta...")
                    detector.state.no_face_alert_sent = True
                    frame_alerta = frame.copy() 
                    _post_obstruction_alerta("http://127.0.0.1:5000", id_usuario, id_vehiculo, elapsed_no_face, frame_alerta)

            elif ear is not None and detector.state.threshold_ear is not None:
            
                if detector.state.no_face_start_ts is not None:
                    detector.state.no_face_start_ts = None
                    detector.state.no_face_alert_sent = False
                    detector._stop_beep() 
             
                if ear < detector.state.threshold_ear:
                    if detector.state.closed_start_ts is None:
                        detector.state.closed_start_ts = now
                else:   
                    if detector.state.closed_start_ts is not None:
                        duracion = now - detector.state.closed_start_ts
                        if duracion >= detector.cfg.min_close_seconds and detector.state.critical_alert_sent is False:
                            detector.state.last_alert_duration = duracion
                            detector.state.total_somnolencia_time += duracion
                        
                        detector.state.closed_start_ts = None
                        detector.state.critical_alert_sent = False
                        detector._stop_beep() 
            
                if detector.state.closed_start_ts is not None:
                    elapsed_somnolencia = now - detector.state.closed_start_ts
                    
                    if elapsed_somnolencia >= detector.cfg.min_close_seconds:
                        somnoliento = True
                        detector._start_beep()
                        if detector.state.alert_start_frame is None:
                             detector.state.alert_start_frame = frame.copy()
                             
                    CRITICAL_THRESHOLD_SECONDS = 11.0
                    if elapsed_somnolencia > CRITICAL_THRESHOLD_SECONDS and detector.state.critical_alert_sent is False:
                        print(f"[Detector] UMBRAL CRÍTICO ({CRITICAL_THRESHOLD_SECONDS}s) ALCANZADO. Enviando alerta...")
                        detector.state.critical_alert_sent = True 
                        frame_alerta = detector.state.alert_start_frame
                        _post_alerta("http://127.0.0.1:5000", id_usuario, id_vehiculo, elapsed_somnolencia, frame_alerta)
                else:
                    if detector.state.no_face_start_ts is None: 
                        detector._stop_beep()
            else:
                detector._stop_beep()
                
            alerta_result = detector.consume_alert_if_ready()
            if alerta_result:
                duracion, frame_alerta = alerta_result
                _post_alerta("http://127.0.0.1:5000", id_usuario, id_vehiculo, duracion, frame_alerta)

            if somnoliento:
                cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 10)
                alert_text = ""
                if detector.state.no_face_start_ts is not None:
                    alert_text = ""
                cv2.putText(frame, alert_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
         
            camera_buffer.set_frame(frame)
            time.sleep(0.02) 
            
    except Exception as e:
        print(f"[Detector] Error durante ejecución: {e}")
    finally:
        detector._stop_beep()
        cap.release()
        detector.face_mesh.close()
        print("[Detector] Finalizado correctamente.")


def iniciar_detector(id_usuario: int, id_vehiculo: int):
    global _detector_thread, _stop_flag, camera_buffer

    if os.getenv("APP_DISABLE_DETECTOR", "0") == "1":
        print("[Detector] Deshabilitado por APP_DISABLE_DETECTOR=1 (modo tests).")
        return

    if _detector_thread and _detector_thread.is_alive():
        print("[Detector] Ya hay un detector activo.")
        return
    
    camera_buffer.reset() 
    
    _stop_flag.clear()
    _detector_thread = threading.Thread(
        target=_detector_thread_func, args=(id_usuario, id_vehiculo), daemon=True
    )
    _detector_thread.start()
    print("[Detector] Hilo de monitoreo iniciado.")

def detener_detector():
    global _detector_thread, _stop_flag

    if os.getenv("APP_DISABLE_DETECTOR", "0") == "1":
        print("[Detector] Deshabilitado (modo tests). Nada que detener.")
        return

    if not _detector_thread or not _detector_thread.is_alive():
        print("[Detector] No hay detector activo.")
        return

    print("[Detector] Señal de parada enviada.")
    _stop_flag.set()
    _detector_thread.join(timeout=5)