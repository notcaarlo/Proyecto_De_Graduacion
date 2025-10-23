# run_detector.py
import argparse
import time
from datetime import datetime
import requests

from ia_module.mediapipe_detector import SomnolenceDetector, DetectorConfig


def nivel_por_duracion(seg: float) -> str:
    if seg < 2.0:
        return "bajo"
    elif seg < 4.0:
        return "medio"
    return "critico"


def post_alerta(server: str, id_usuario: int, id_vehiculo: int, duracion: float):
    url = f"{server.rstrip('/')}/api/alertas"
    payload = {
        "id_usuario": id_usuario,
        "id_vehiculo": id_vehiculo,
        "duracion": round(duracion, 2),
        "nota": f"EAR por debajo de umbral (auto) @ {datetime.now().isoformat(timespec='seconds')}",
        "nivel_somnolencia": nivel_por_duracion(duracion)
    }
    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code >= 400:
            print(f"[API] Error {r.status_code}: {r.text}")
        else:
            print(f"[API] Alerta enviada: {payload}")
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

    # Iniciar captura + detección en otro bucle y consumir alertas cuando ocurran
    # (Implementación simple: ejecutamos el detector en el hilo principal y
    # consultamos periódicamente si hay alertas cerradas para postear).
    import threading

    def loop_detector():
        det.run(camera_index=args.camera)

    t = threading.Thread(target=loop_detector, daemon=True)
    t.start()

    try:
        print("[Main] Enviará alertas a:", args.server)
        while t.is_alive():
            dur = det.consume_alert_if_ready()
            if dur is not None:
                post_alerta(args.server, args.user, args.vehiculo, dur)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    print("[Main] Saliendo...")


if __name__ == "__main__":
    main()
