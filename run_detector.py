# run_detector.py
import argparse
import time
from datetime import datetime
import requests
import cv2  # <-- Necesario para codificar la imagen
import threading

# Asegúrate de que el nombre del módulo sea correcto
from ia_module.mediapipe_detector import SomnolenceDetector, DetectorConfig


def nivel_por_duracion(seg: float) -> str:
    if seg < 2.0:
        return "bajo"
    elif seg < 4.0:
        return "medio"
    return "critico"


# --- Modificado para aceptar el 'frame' ---
def post_alerta(server: str, id_usuario: int, id_vehiculo: int, duracion: float, frame):
    url = f"{server.rstrip('/')}/api/alertas"
    
    # --- Datos del formulario (como strings) ---
    data = {
        "id_usuario": str(id_usuario),
        "id_vehiculo": str(id_vehiculo),
        "duracion": str(round(duracion, 2)),
        "nota": f"EAR por debajo de umbral (auto) @ {datetime.now().isoformat(timespec='seconds')}",
        "nivel_somnolencia": nivel_por_duracion(duracion)
    }

    # --- Preparar el archivo de imagen ---
    files = None
    if frame is not None:
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            files = {
                'evidencia_img': ('evidencia.jpg', frame_bytes, 'image/jpeg')
            }
            print("[API] Adjuntando imagen de evidencia.")
        except Exception as e:
            print(f"[API] Error al codificar la imagen: {e}")

    # --- Enviar como 'multipart/form-data' ---
    try:
        r = requests.post(url, data=data, files=files, timeout=5)
        
        if r.status_code >= 400:
            print(f"[API] Error {r.status_code}: {r.text}")
        else:
            print(f"[API] Alerta enviada: {data['nivel_somnolencia']} ({data['duracion']}s)")
    except requests.RequestException as e:
        print(f"[API] Error de red: {e}")


def main():
    parser = argparse.ArgumentParser(description="Detector de somnolencia (MediaPipe + OpenCV)")
    parser.add_argument("--server", default="http://127.0.0.1:5000", help="URL del backend Flask")
    parser.add_argument("--user", type=int, required=True, help="ID de usuario (conductOR)")
    parser.add_argument("--vehiculo", type=int, required=True, help="ID de vehiculo")
    parser.add_argument("--camera", type=int, default=0, help="Indice de camara (0 por defecto)")
    parser.add_argument("--minclose", type=float, default=1.5, help="Segundos min. ojos cerrados para alerta")
    parser.add_argument("--calib", type=float, default=3.0, help="Segundos de calibracion inicial")
    parser.add_argument("--ratio", type=float, default=0.75, help="Umbral = EAR_base * ratio (0-1)")
    args = parser.parse_args()

    cfg = DetectorConfig(
        calibration_seconds=args.calib,
        threshold_ratio=args.ratio,
        min_close_seconds=args.minclose,
        draw_landmarks=True
    )

    det = SomnolenceDetector(cfg)

    def loop_detector():
        # --- CORREGIDO: Llama a det.run() ---
        det.run(camera_index=args.camera)

    t = threading.Thread(target=loop_detector, daemon=True)
    t.start()

    print("[Main] Enviará alertas a:", args.server)
    try:
        while t.is_alive():
            
            # --- Modificado para esperar (duracion, frame) ---
            result = det.consume_alert_if_ready() 
            
            if result is not None:
                duracion, frame = result 
                post_alerta(args.server, args.user, args.vehiculo, duracion, frame)
                
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    print("[Main] Saliendo...")


if __name__ == "__main__":
    main()