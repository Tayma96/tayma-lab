"""Yayıncının yüz kamerasını otomatik bulur.

Fikir AI-Youtube-Shorts-Generator'ın OpenCV yüz takibinden (MIT) geliyor, ama yayın formatına
uyarlandı: oradaki gibi yüzü takip edip kırpmak yerine, klip boyunca hep AYNI yerde duran küçük
bir yüz arıyoruz (oyundaki karakter yüzleri hareket eder, yüz kamerası sabit durur). Bulunan
konum, üstte yüz kamerası ve altta oyun olan bölünmüş düzen için kullanılır.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def sample_faces(video: Path, samples: int = 12) -> tuple[list[list[tuple[float, float, float, float]]], int]:
    """Videodan eşit aralıklı kareler alır, her karedeki yüzleri (x, y, w, h oranları) döner."""
    import cv2

    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    W = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1
    H = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    frames: list[list[tuple[float, float, float, float]]] = []
    for i in range(samples):
        if total:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (i + 0.5) / samples))
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6,
                                         minSize=(int(H * 0.05), int(H * 0.05)))
        frames.append([(x / W, y / H, w / W, h / H) for (x, y, w, h) in found])
    cap.release()
    return frames, len(frames)


def stable_face(frames: list[list[tuple[float, float, float, float]]], *, min_ratio: float = 0.5,
                tol: float = 0.06, max_area: float = 0.06) -> tuple[float, float, float, float] | None:
    """Saf fonksiyon. Karelerin en az yarısında neredeyse aynı yerde duran küçük yüzü bulur."""
    n = len(frames)
    if n == 0:
        return None
    candidates = [f for faces in frames for f in faces if f[2] * f[3] <= max_area]
    best, best_hits = None, 0
    for cx, cy, cw, ch in candidates:
        mx, my = cx + cw / 2, cy + ch / 2
        hits, members = 0, []
        for faces in frames:
            match = [f for f in faces if abs(f[0] + f[2] / 2 - mx) < tol and abs(f[1] + f[3] / 2 - my) < tol]
            if match:
                hits += 1
                members.append(match[0])
        if hits > best_hits:
            best_hits = hits
            best = tuple(sum(m[i] for m in members) / len(members) for i in range(4))
    if best is None or best_hits / n < min_ratio:
        return None
    return best  # type: ignore[return-value]


def face_to_cam(face: tuple[float, float, float, float], src_aspect: float = 16 / 9,
                panel_aspect: float = 1080 / 640) -> dict:
    """Yüz kutusunu, üst paneldeki (1080x640) oranla aynı oranda bir kamera çerçevesine genişletir
    (yüz genişliğinin ~3.2 katı)."""
    x, y, w, h = face
    cam_w = min(1.0, w * 3.2)
    cam_h = min(1.0, cam_w * src_aspect / panel_aspect)
    cx, cy = x + w / 2, y + h / 2 + h * 0.2   # omuzlar da girsin diye hafif aşağı
    left = min(max(0.0, cx - cam_w / 2), 1 - cam_w)
    top = min(max(0.0, cy - cam_h / 2), 1 - cam_h)
    return {"x": round(left, 4), "y": round(top, 4), "w": round(cam_w, 4), "h": round(cam_h, 4)}


class FacecamCache:
    """Her yayıncının yüz kamerası konumunu bir kez bulur ve data/facecams.json'da saklar."""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict = json.loads(path.read_text()) if path.exists() else {}

    def get(self, broadcaster: str, video: Path) -> dict | None:
        key = broadcaster.lower()
        if key in self.data:
            return self.data[key]
        try:
            frames, _ = sample_faces(video)
        except ImportError:
            log.warning("opencv kurulu değil, yüz kamerası tespiti atlanıyor")
            return None
        face = stable_face(frames)
        cam = face_to_cam(face) if face else None
        log.info("%s için yüz kamerası: %s", broadcaster, cam or "bulunamadı (bulanık düzen)")
        # Sadece bulunanı kalıcı sakla; bulunamadıysa bir sonraki klipte tekrar denensin
        if cam:
            self.data[key] = cam
            self.path.write_text(json.dumps(self.data, indent=2))
        return cam
