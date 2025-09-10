# app/modules/vision.py
import threading
import time
import tempfile
import os
import math
import copy
import json

try:
    from maix import camera, image, nn, display
except (ImportError, ModuleNotFoundError):
    print("!!! maix library not found, switching to MOCK mode for development. !!!")
    from .maix_mock import camera, image, nn

# --- 常量定义 ---
NANOTRACK_MODEL_PATH = "/root/models/nanotrack.mud"
TEMP_FRAME_PATH = os.path.join(tempfile.gettempdir(), "vision_frame.jpg")

# --- 颜色阈值字典 ---
COLOR_THRESHOLDS = {
    "orange": ([[0, 80, 40, 60, 40, 80]], 2),
    "blue": ([[0, 80, -10, 10, -55, -30]], 0),
    "yellow": ([[0, 80, -15, 15, 50, 80]], 1),
    "purple": ([[28, 68, 12, 52, -80, -40]], 3),
}

# --- 内置信息字典 ---
ORGANS_INFO = {
    "ORG-2025-0001": {
        "编号": "ORG-2025-0001",
        "类型": "结肠类器官",
        "供体": "DONOR-001",
        "位置": {"架": "Rack-1", "盒": "Box-01"},
    },
    "ORG-2025-0002": {
        "编号": "ORG-2025-0002",
        "类型": "肝脏类器官",
        "供体": "DONOR-002",
        "位置": {"架": "Rack-2", "盒": "Box-02"},
    },
    "ORG-2025-0003": {
        "编号": "ORG-2025-0003",
        "类型": "章鱼蛋蛋",
        "供体": "DONOR-003",
        "位置": {"架": "Rack-2", "盒": "Box-02"},
    },
}


# --- 视觉处理器状态定义 ---
class VisionState:
    IDLE = 0
    PENDING_INIT = 1
    INITIALIZING = 2
    TRACKING = 3


class VisionProcessor:
    def __init__(self, width=320, height=240):
        # --- [核心修改] YOLO已完全移除 ---
        self.detector = None
        print("--- YOLOv5 detection is permanently disabled. ---")

        self.cam = camera.Camera(width, height)
        print(f"Camera Initialized ({width}x{height})")

        self.disp = None
        try:
            self.disp = display.Display()
            print("Local display initialized successfully.")
        except Exception as e:
            print(f"!!! Failed to initialize local display: {e}")

        self.tracker = None
        try:
            if os.path.exists(NANOTRACK_MODEL_PATH):
                self.tracker = nn.NanoTrack(model=NANOTRACK_MODEL_PATH)
                print(f"NanoTrack model loaded.")
        except Exception as e:
            print(f"!!! Failed to load NanoTrack model: {e}")

        self.center_x = width // 2
        self.center_y = height // 2
        self.blob_detection_enabled = True
        self.qrcode_detection_enabled = True
        self.active_blob_color_key = "red"
        self.BLOB_PIXELS_THRESHOLD = 150
        self.APRILTAG_FAMILIES = image.ApriltagFamilies.TAG36H11
        self.APRILTAG_DISTANCE_FACTOR_K = 20.0

        self.state = VisionState.IDLE
        self.init_rect = None
        self.init_start_time = 0
        self.INIT_TIMEOUT = 3.0

        self.latest_jpeg = None
        self.latest_data = {
            "color_block": {"detected": False},
            "apriltag": {"detected": False},
            "nanotrack": {"detected": False, "status": "IDLE"},
            "qrcode": {"detected": False, "payload": None},
        }
        self.lock = threading.Lock()
        self.stopped = False
        self.thread = threading.Thread(target=self.run, daemon=True)

    def _initialize_tracker_task(self, img_copy, x, y, w, h):
        try:
            self.tracker.init(img_copy, x, y, w, h)
            with self.lock:
                if self.state == VisionState.INITIALIZING:
                    self.state = VisionState.TRACKING
        except Exception as e:
            with self.lock:
                self.state = VisionState.IDLE
                self.latest_data["nanotrack"] = {
                    "detected": False,
                    "status": "INIT_FAILED",
                }

    def start_tracking(self, x, y, w, h):
        if not self.tracker:
            return False
        with self.lock:
            self.init_rect = (x, y, w, h)
            self.state = VisionState.PENDING_INIT
            self.latest_data["nanotrack"] = {
                "detected": False,
                "status": "PENDING_INIT",
            }
        return True

    def stop_tracking(self):
        with self.lock:
            self.state = VisionState.IDLE
            self.init_rect = None
        print("Tracking stopped. State reset to IDLE.")

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopped = True

    def run(self):
        while not self.stopped:
            img = self.cam.read()
            if not img:
                time.sleep(0.01)
                continue

            current_state = self.state

            if current_state == VisionState.PENDING_INIT:
                if self.init_rect:
                    x, y, w, h = self.init_rect
                    init_thread = threading.Thread(
                        target=self._initialize_tracker_task,
                        args=(img, x, y, w, h),
                    )
                    init_thread.daemon = True
                    init_thread.start()
                    with self.lock:
                        self.state = VisionState.INITIALIZING
                        self.init_start_time = time.time()
                        self.init_rect = None

            elif current_state == VisionState.INITIALIZING:
                if time.time() - self.init_start_time > self.INIT_TIMEOUT:
                    self.stop_tracking()

            if self.state == VisionState.TRACKING:
                track_data = self._track_target(img)
                with self.lock:
                    self.latest_data.update(
                        {
                            "color_block": {"detected": False},
                            "apriltag": {"detected": False},
                            "qrcode": {"detected": False, "payload": None},
                            "nanotrack": track_data,
                        }
                    )
            elif self.state == VisionState.IDLE:
                blob_data = (
                    self._detect_blobs(img)
                    if self.blob_detection_enabled
                    else {"detected": False}
                )
                apriltag_data = self._detect_apriltags(img)
                qrcode_data = (
                    self._detect_qrcodes(img)
                    if self.qrcode_detection_enabled
                    else {"detected": False, "payload": None}
                )
                with self.lock:
                    self.latest_data.update(
                        {
                            "color_block": blob_data,
                            "apriltag": apriltag_data,
                            "qrcode": qrcode_data,
                            "nanotrack": {"detected": False, "status": "IDLE"},
                        }
                    )

            err = img.save(TEMP_FRAME_PATH, quality=90)
            jpeg_bytes = None
            if err == 0:
                with open(TEMP_FRAME_PATH, "rb") as f:
                    jpeg_bytes = f.read()
            with self.lock:
                self.latest_jpeg = jpeg_bytes
            if self.disp:
                try:
                    self.disp.show(img)
                except Exception as e:
                    self.disp = None
            time.sleep(0.05)

    def _track_target(self, img):
        if not self.tracker:
            return {"detected": False, "status": "ERROR"}
        try:
            r = self.tracker.track(img)
            if r.w > 0 and r.h > 0:
                img.draw_rect(r.x, r.y, r.w, r.h, image.COLOR_RED, 3)
                img.draw_string(
                    r.x, r.y - 15, f"Tracking: {r.score:.2f}", image.COLOR_RED
                )
                return {
                    "detected": True,
                    "status": "TRACKING",
                    "x": r.x,
                    "y": r.y,
                    "w": r.w,
                    "h": r.h,
                    "score": round(r.score, 2),
                }
        except Exception as e:
            self.stop_tracking()
        return {"detected": False, "status": "LOST"}

    def _detect_qrcodes(self, img):
        qrcodes = img.find_qrcodes()
        if not qrcodes:
            return {"detected": False, "payload": None}

        qr = qrcodes[0]
        corners = qr.corners()
        for i in range(4):
            img.draw_line(
                corners[i][0],
                corners[i][1],
                corners[(i + 1) % 4][0],
                corners[(i + 1) % 4][1],
                image.COLOR_RED,
            )

        payload = qr.payload()
        show_info = None
        display_str = ""

        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            data = json.loads(payload)
            code = data.get("编号")
            if code and code in ORGANS_INFO:
                info = ORGANS_INFO[code]
                show_info = "\n".join(
                    [
                        f"编号: {info['编号']}",
                        f"类型: {info['类型']}",
                        f"供体: {info['供体']}",
                        f"位置: {info['位置']}",
                    ]
                )
                display_str = f"{info['编号']} {info['类型']}"
            else:
                show_info = "\n".join(f"{k}: {v}" for k, v in data.items())
                key, value = next(iter(data.items()))
                display_str = f"{key}: {value}"
        except Exception:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="replace")
            if payload in ORGANS_INFO:
                info = ORGANS_INFO[payload]
                show_info = "\n".join(
                    [
                        f"编号: {info['编号']}",
                        f"类型: {info['类型']}",
                        f"供体: {info['供体']}",
                        f"位置: {info['位置']}",
                    ]
                )
                display_str = f"{info['编号']} {info['类型']}"
            else:
                show_info = payload
                display_str = payload[:10]

        img.draw_string(qr.x(), qr.y() - 15, display_str, image.COLOR_RED)

        return {"detected": True, "payload": show_info}

    def set_blob_detection_status(self, enabled):
        self.blob_detection_enabled = bool(enabled)
        return self.blob_detection_enabled

    def set_qrcode_detection_status(self, enabled):
        self.qrcode_detection_enabled = bool(enabled)
        return self.qrcode_detection_enabled

    def set_blob_color_key(self, color_key):
        if color_key in COLOR_THRESHOLDS:
            self.active_blob_color_key = color_key
            return True, f"Color set to {color_key}"
        else:
            return False, f"Invalid color: {color_key}"

    def _detect_blobs(self, img):
        thresholds, color_index = COLOR_THRESHOLDS.get(
            self.active_blob_color_key, (None, -1)
        )
        if not thresholds:
            return {"detected": False}

        blobs = img.find_blobs(
            thresholds, pixels_threshold=self.BLOB_PIXELS_THRESHOLD, merge=True
        )
        if blobs:
            largest_blob = max(blobs, key=lambda b: b.area())
            corners = largest_blob.mini_corners()
            _, rotation_deg = calculate_angle_from_corners(corners)
            offset_x = largest_blob.cx() - self.center_x
            offset_y = largest_blob.cy() - self.center_y
            for i in range(4):
                p1, p2 = corners[i], corners[(i + 1) % 4]
                img.draw_line(p1[0], p1[1], p2[0], p2[1], image.COLOR_GREEN, 2)
            return {
                "offset_x": int(offset_x),
                "offset_y": int(offset_y),
                "w": int(largest_blob.w()),
                "h": int(largest_blob.h()),
                "angle": float(rotation_deg),
                "detected": True,
                "color_name": self.active_blob_color_key,
                "color_index": color_index,
            }
        return {"detected": False}

    def _detect_apriltags(self, img):
        tags = img.find_apriltags(families=self.APRILTAG_FAMILIES)
        if tags:
            tag = tags[0]
            cx, cy = tag.cx(), tag.cy()
            offset_x = cx - self.center_x
            offset_y = cy - self.center_y
            real_distance = int(
                abs(self.APRILTAG_DISTANCE_FACTOR_K * tag.z_translation())
            )
            corners = tag.corners()
            for i in range(4):
                p1, p2 = corners[i], corners[(i + 1) % 4]
                img.draw_line(p1[0], p1[1], p2[0], p2[1], image.COLOR_GREEN, 2)
            img.draw_cross(cx, cy, image.COLOR_GREEN, 10)
            img.draw_string(cx + 10, cy, f"Dist: {real_distance} mm", image.COLOR_GREEN)
            return {
                "id": int(tag.id()),
                "offset_x": int(offset_x),
                "offset_y": int(offset_y),
                "distance": int(real_distance),
                "detected": True,
            }
        return {"detected": False}

    def get_latest_frame(self):
        with self.lock:
            return self.latest_jpeg

    def get_latest_data(self):
        with self.lock:
            return copy.deepcopy(self.latest_data)


def calculate_angle_from_corners(corners):
    dx1, dy1 = corners[1][0] - corners[0][0], corners[1][1] - corners[0][1]
    len_sq1 = dx1**2 + dy1**2
    dx2, dy2 = corners[2][0] - corners[1][0], corners[2][1] - corners[1][1]
    len_sq2 = dx2**2 + dy2**2
    final_dx, final_dy = (dx1, dy1) if len_sq1 > len_sq2 else (dx2, dy2)
    rotation_rad = math.atan2(final_dy, final_dx)
    rotation_deg = math.degrees(rotation_rad)
    if rotation_deg < 0:
        rotation_deg += 180
    if rotation_deg > 90:
        rotation_deg -= 90
    return rotation_rad, rotation_deg
