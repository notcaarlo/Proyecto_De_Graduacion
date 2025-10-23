import time
import platform
import threading
from dataclasses import dataclass
from typing import Tuple, Optional
import cv2
import numpy as np
import mediapipe as mp
import os

# ==============================
# Índices de ojos para EAR (MediaPipe FaceMesh)
# ==============================
LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [263, 387, 385, 362, 380, 373]


def _euclidean(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.linalg.norm(p1 - p2))


def _ear_from_landmarks(landmarks: np.ndarray, eye_idx: list) -> float:
    p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_idx]
    return (_euclidean(p2, p6) + _euclidean(p3, p5)) / (
        2.0 * _euclidean(p1, p4) + 1e-8
    )


# ==============================
# Configuración del detector
# ==============================
@dataclass
class DetectorConfig:
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    calibration_seconds: float = 6.0
    threshold_ratio: float = 0.75
    min_close_seconds: float = 1.5
    draw_landmarks: bool = False


# ==============================
# Estado interno del detector
# ==============================
@dataclass
class DetectionState:
    ear_open_baseline: Optional[float] = None
    threshold_ear: Optional[float] = None
    closed_start_ts: Optional[float] = None
    last_alert_duration: float = 0.0
    total_alerts: int = 0
    total_somnolence_time: float = 0.0


# ==============================
# Clase principal del detector
# ==============================
class SomnolenceDetector:
    def __init__(self, config: DetectorConfig):
        self.cfg = config
        self.state = DetectionState()
        self._mp_face_mesh = mp.solutions.face_mesh
        self._beep_running = False

    # ----------------------------------------------------
    # Sonido continuo (beep)
    # ----------------------------------------------------
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

    # ----------------------------------------------------
    # EAR (Eye Aspect Ratio)
    # ----------------------------------------------------
    def _calc_ears(self, frame_bgr, results) -> Tuple[Optional[float], Optional[float]]:
        if not results.multi_face_landmarks:
            return None, None

        h, w = frame_bgr.shape[:2]
        face = results.multi_face_landmarks[0]
        pts = np.array([[lm.x * w, lm.y * h] for lm in face.landmark], dtype=np.float32)

        left_ear = _ear_from_landmarks(pts, LEFT_EYE_IDX)
        right_ear = _ear_from_landmarks(pts, RIGHT_EYE_IDX)
        return left_ear, right_ear

    # ----------------------------------------------------
    # Calibración inicial
    # ----------------------------------------------------
    def calibrate(self, cap) -> float:
        print("[Calibración] Mantén los ojos abiertos y mira a la cámara...")
        ears = []
        start = time.time()

        with self._mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=self.cfg.min_detection_confidence,
            min_tracking_confidence=self.cfg.min_tracking_confidence,
        ) as fm:
            while time.time() - start < self.cfg.calibration_seconds:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = fm.process(frame_rgb)
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

    # ----------------------------------------------------
    # Ejecución principal (controlada paso a paso)
    # ----------------------------------------------------
    def run_step(self, cap):
        ok, frame = cap.read()
        if not ok:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        with self._mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=self.cfg.min_detection_confidence,
            min_tracking_confidence=self.cfg.min_tracking_confidence,
        ) as fm:
            results = fm.process(frame_rgb)

        l_ear, r_ear = self._calc_ears(frame, results)
        ear = (l_ear + r_ear) / 2.0 if l_ear and r_ear else None

        now = time.time()
        somnoliento = False

        # Nueva lógica: solo una alerta por episodio completo
        if ear is not None and self.state.threshold_ear is not None:
            if ear < self.state.threshold_ear:
                # Ojos cerrados
                if self.state.closed_start_ts is None:
                    self.state.closed_start_ts = now
            else:
                # Ojos abiertos: si hubo cierre largo, genera alerta
                if self.state.closed_start_ts is not None:
                    duracion = now - self.state.closed_start_ts
                    if duracion >= self.cfg.min_close_seconds:
                        self.state.last_alert_duration = duracion
                        self.state.total_somnolence_time += duracion
                    self.state.closed_start_ts = None
                    self._stop_beep()
                else:
                    self.state.last_alert_duration = 0.0

            # Solo activar alerta visual/beep si pasa el umbral
            if self.state.closed_start_ts is not None:
                elapsed = now - self.state.closed_start_ts
                if elapsed >= self.cfg.min_close_seconds:
                    somnoliento = True
                    self._start_beep()
            else:
                self._stop_beep()
        else:
            self._stop_beep()

        # Mostrar overlay si hay somnolencia
        if somnoliento:
            overlay = frame.copy()
            cv2.rectangle(
                overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1
            )
            alpha = 0.8
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            cv2.putText(
                frame,
                "ALERTA DE SOMNOLENCIA",
                (40, int(frame.shape[0] / 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                (0, 0, 255),
                3,
                cv2.LINE_AA,
            )

        cv2.imshow("Detector Somnolencia", frame)
        cv2.waitKey(1)

    # ----------------------------------------------------
    # Enviar alertas una sola vez por episodio
    # ----------------------------------------------------
    def consume_alert_if_ready(self) -> Optional[dict]:
        """
        Devuelve un diccionario con la duración y nivel de somnolencia
        cuando un episodio finaliza (solo una vez por cierre de ojos completo).
        """
        if self.state.last_alert_duration > 0.0:
            dur = self.state.last_alert_duration
            self.state.last_alert_duration = 0.0
            self.state.total_alerts += 1

            # Determinar nivel según duración
            if dur < 2.0:
                nivel = "bajo"
            elif dur < 4.0:
                nivel = "medio"
            else:
                nivel = "critico"

            return {
                "duracion": round(dur, 2),
                "nivel_somnolencia": nivel,
            }
        return None
