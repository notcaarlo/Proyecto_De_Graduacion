# app/utils/detector_launcher.py
import os
import threading
import time
import requests

# Variables globales de control
_stop_flag = threading.Event()
_detector_thread = None


def _post_alerta(server: str, id_usuario: int, id_vehiculo: int, data: dict):
    """
    Envía una alerta al backend Flask usando /api/alertas.
    Espera un dict con al menos: {"duracion": float, "nivel_somnolencia": str}
    """
    url = f"{server.rstrip('/')}/api/alertas"
    payload = {
        "id_usuario": id_usuario,
        "id_vehiculo": id_vehiculo,
        "duracion": data["duracion"],
        "nota": "Alerta automática del detector",
        "nivel_somnolencia": data["nivel_somnolencia"],
    }

    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code == 201:
            print(f"[API] ✅ Alerta enviada correctamente: {payload}")
        else:
            print(f"[API] ❌ Error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[API] ⚠️ Error al enviar alerta: {e}")


def _detector_thread_func(id_usuario, id_vehiculo):
    """
    Hilo de ejecución del detector.
    Hacemos import LAZY aquí para que en tests (APP_DISABLE_DETECTOR=1) no requiera mediapipe ni cámara.
    """
    try:
        from ia_module.mediapipe_detector import SomnolenceDetector, DetectorConfig
        import cv2
    except Exception as e:
        print(f"[Detector] Import lazy falló (mediapipe/cv2 no disponibles): {e}")
        return

    print(f"[Detector] Iniciando para usuario={id_usuario}, vehiculo={id_vehiculo}")
    cfg = DetectorConfig(
        calibration_seconds=6.0,
        threshold_ratio=0.75,
        min_close_seconds=1.5,
        draw_landmarks=False,
    )
    detector = SomnolenceDetector(cfg)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[Detector] ❌ Error: no se pudo abrir la cámara.")
        return

    # Calibración inicial
    detector.calibrate(cap)
    print("[Detector] ✅ Cámara activa, monitoreo iniciado.")

    try:
        while not _stop_flag.is_set():
            # Avanzar un paso de detección/visualización
            detector.run_step(cap)

            # Si hay una alerta lista, enviarla
            alerta = detector.consume_alert_if_ready()
            if alerta:
                _post_alerta("http://127.0.0.1:5000", id_usuario, id_vehiculo, alerta)

            time.sleep(0.05)
    except Exception as e:
        print(f"[Detector] ⚠️ Error durante ejecución: {e}")
    finally:
        cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[Detector] 📴 Finalizado correctamente.")


def iniciar_detector(id_usuario: int, id_vehiculo: int):
    """
    Inicia el detector en un hilo nuevo (si no hay uno activo).
    En modo tests (APP_DISABLE_DETECTOR=1) no hace nada.
    """
    global _detector_thread, _stop_flag

    # Modo stub para pruebas automatizadas
    if os.getenv("APP_DISABLE_DETECTOR", "0") == "1":
        print("[Detector] Deshabilitado por APP_DISABLE_DETECTOR=1 (modo tests).")
        return

    if _detector_thread and _detector_thread.is_alive():
        print("[Detector] Ya hay un detector activo.")
        return

    _stop_flag.clear()
    _detector_thread = threading.Thread(
        target=_detector_thread_func, args=(id_usuario, id_vehiculo), daemon=True
    )
    _detector_thread.start()
    print("[Detector] 🚀 Hilo de monitoreo iniciado.")


def detener_detector():
    """
    Detiene el detector de somnolencia y cierra la cámara.
    En modo tests (APP_DISABLE_DETECTOR=1) no hace nada.
    """
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
    print("[Detector] ✅ Cámara y detector cerrados.")
