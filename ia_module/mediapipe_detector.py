import time
import platform
import threading
from dataclasses import dataclass, field
from typing import Tuple, Optional
import cv2
import numpy as np
import mediapipe as mp
import os

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [263, 387, 385, 362, 380, 373]

def _euclidean(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.linalg.norm(p1 - p2))

# Calculo EAR
def _ear_from_landmarks(landmarks: np.ndarray, eye_idx: list) -> float:
    # Extrae los landmarks del ojo.
    p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_idx]
    vert1 = _euclidean(p2, p6)  # Primera distancia vertical
    vert2 = _euclidean(p3, p5)  # Segunda distancia vertical

    # Ancho del ojo
    horiz = _euclidean(p1, p4)

    # EAR = (vert1 + vert2) / (2 * horiz)
    return (vert1 + vert2) / (2.0 * horiz + 1e-8) # epsilon (1e-8) para evitar división por cero
@dataclass
class DetectorConfig:
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    calibration_seconds: float = 6.0
    threshold_ratio: float = 0.75
    min_close_seconds: float = 1.5
    draw_landmarks: bool = False
@dataclass
class DetectionState:
    ear_open_baseline: Optional[float] = None
    threshold_ear: Optional[float] = None
    closed_start_ts: Optional[float] = None
    last_alert_duration: float = 0.0
    critical_alert_sent: bool = False 
    alert_start_frame: Optional[np.ndarray] = field(default=None, repr=False)
    no_face_start_ts: Optional[float] = None
    no_face_alert_sent: bool = False
    total_alerts: int = 0
    total_somnolencia_time: float = 0.0
class SomnolenceDetector:
    def __init__(self, config: DetectorConfig):
        self.cfg = config
        self.state = DetectionState()
        self._beep_running = False

        self._mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self._mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=self.cfg.min_detection_confidence,
            min_tracking_confidence=self.cfg.min_tracking_confidence,
        )

    def _beep_continuous(self):
        while self._beep_running:
            try:
                if platform.system() == "Windows":
                    import winsound
                    winsound.Beep(1000, 300)
                else:
                    os.system("play -nq -t alsa synth 0.3 sine 1000")
            except Exception as e:
                print(f"[Sonido] Error beep continuo: {e}")
            time.sleep(0.1)

    def _start_beep(self):
        if not self._beep_running:
            self._beep_running = True
            threading.Thread(target=self._beep_continuous, daemon=True).start()

    def _stop_beep(self):
        if self._beep_running:
            self._beep_running = False

    def _calc_ears(self, frame_bgr, results) -> Tuple[Optional[float], Optional[float]]:
        if not results.multi_face_landmarks:
            return None, None

        h, w = frame_bgr.shape[:2]
        face = results.multi_face_landmarks[0]
        pts = np.array([[lm.x * w, lm.y * h] for lm in face.landmark], dtype=np.float32)

        left_ear = _ear_from_landmarks(pts, LEFT_EYE_IDX)
        right_ear = _ear_from_landmarks(pts, RIGHT_EYE_IDX)
        return left_ear, right_ear

    def calibrate(self, cap) -> float:
        print("[Calibración] Mantén los ojos abiertos y mira a la cámara...")
        ears = []
        start = time.time()

        while time.time() - start < self.cfg.calibration_seconds:
            ok, frame = cap.read()
            if not ok:
                continue
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(frame_rgb)
            
            l, r = self._calc_ears(frame, results)
            if l is not None and r is not None:
                ears.append((l + r) / 2.0)
            cv2.putText(
                frame,
                "Calibrando... mira al frente (ojos abiertos)",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )
            cv2.imshow("Detector Somnolencia - Calibracion", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyWindow("Detector Somnolencia - Calibracion")

        if not ears:
            raise RuntimeError("No se pudo calibrar: no se detectaron ojos/cara.")

        baseline = float(np.median(ears))
        self.state.ear_open_baseline = baseline
        self.state.threshold_ear = baseline * self.cfg.threshold_ratio
        print(
            f"[Calibración] EAR base: {baseline:.3f} | Umbral: {self.state.threshold_ear:.3f}"
        )
        return baseline
    
    def consume_alert_if_ready(self) -> Optional[Tuple[float, Optional[np.ndarray]]]:
        """
        Devuelve (duracion, frame) si un episodio de alerta (Bajo o Medio) ha finalizado.
        """
        if self.state.last_alert_duration > 0.0:
            dur = self.state.last_alert_duration
            frame = self.state.alert_start_frame
            
            self.state.last_alert_duration = 0.0
            self.state.alert_start_frame = None
            self.state.total_alerts += 1
            
            return round(dur, 2), frame
        
        return None