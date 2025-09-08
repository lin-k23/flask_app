# app/modules/vision.py
import threading
import time
import tempfile
import os
import math
import copy
import json  # 导入json库

try:
    from maix import camera, image, nn, display
except (ImportError, ModuleNotFoundError):
    print("!!! maix library not found, switching to MOCK mode for development. !!!")
    from .maix_mock import camera, image, nn

# --- 常量定义 ---
MODEL_PATH = "model_234836.mud"
FALLBACK_MODEL_PATH = "/root/models/maixhub/234836/model_234836.mud"
NANOTRACK_MODEL_PATH = "/root/models/nanotrack.mud"
CONF_THRESHOLD = 0.5
IOU_THRESHOLD = 0.45
TEMP_FRAME_PATH = os.path.join(tempfile.gettempdir(), "vision_frame.jpg")


# --- [核心修改] 新增内置信息字典 ---
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
        # --- YOLOv5和摄像头初始化 ---
        self.detector = None
        try:
            model_to_load = (
                MODEL_PATH if os.path.exists(MODEL_PATH) else FALLBACK_MODEL_PATH
            )
            if os.path.exists(model_to_load):
                self.detector = nn.YOLOv5(model=model_to_load)
                width, height = (
                    self.detector.input_width(),
                    self.detector.input_height(),
                )
                print(f"YOLOv5 model loaded. Input size: {width}x{height}")
        except Exception as e:
            print(f"!!! Failed to load YOLOv5 model: {e}")

        self.cam = camera.Camera(width, height)
        print(f"Camera Initialized ({width}x{height})")

        # --- [新增] 初始化本地显示屏 ---
        self.disp = None
        try:
            self.disp = display.Display()
            print("Local display initialized successfully.")
        except Exception as e:
            print(f"!!! Failed to initialize local display: {e}")

        # --- NanoTrack模型加载 ---
        self.tracker = None
        try:
            if os.path.exists(NANOTRACK_MODEL_PATH):
                self.tracker = nn.NanoTrack(model=NANOTRACK_MODEL_PATH)
                print(f"NanoTrack model loaded.")
        except Exception as e:
            print(f"!!! Failed to load NanoTrack model: {e}")

        # --- 其他变量定义 ---
        self.center_x = width // 2
        self.center_y = height // 2
        self.blob_detection_enabled = True
        self.qrcode_detection_enabled = True  # <--- 新增：二维码识别开关
        self.TH_RED = [[0, 80, 40, 80, 10, 80]]
        self.BLOB_PIXELS_THRESHOLD = 150
        self.APRILTAG_FAMILIES = image.ApriltagFamilies.TAG36H11
        self.APRILTAG_DISTANCE_FACTOR_K = 20.0

        # --- 状态管理变量 ---
        self.state = VisionState.IDLE
        self.init_rect = None
        self.init_start_time = 0
        self.INIT_TIMEOUT = 3.0

        self.latest_jpeg = None
        self.latest_data = {
            "color_block": {"detected": False},
            "apriltag": {"detected": False},
            "yolo_objects": {"detected": False, "objects": []},
            "nanotrack": {"detected": False, "status": "IDLE"},
            "qrcode": {"detected": False, "payload": None},  # <--- 新增：二维码数据
        }
        self.lock = threading.Lock()
        self.stopped = False
        self.thread = threading.Thread(target=self.run, daemon=True)

    def _initialize_tracker_task(self, img_copy, x, y, w, h):
        try:
            print(
                f"--> [Thread] Attempting to initialize tracker with rect: {(x, y, w, h)}"
            )
            # 在单独的线程中初始化，避免阻塞主循环
            self.tracker.init(img_copy, x, y, w, h)
            with self.lock:
                if self.state == VisionState.INITIALIZING:
                    self.state = VisionState.TRACKING
                    print(
                        "<-- [Thread] Tracker initialized successfully. State set to TRACKING."
                    )
        except Exception as e:
            print(
                f"!!! [Thread] Tracker initialization failed (likely due to format mismatch): {e}"
            )
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
                    print(f"!!! Tracker initialization timed out! Resetting state.")
                    self.stop_tracking()

            if self.state == VisionState.TRACKING:
                track_data = self._track_target(img)
                with self.lock:
                    # 追踪时，禁用其他检测，并只更新追踪数据
                    self.latest_data.update(
                        {
                            "yolo_objects": {"detected": False, "objects": []},
                            "color_block": {"detected": False},
                            "apriltag": {"detected": False},
                            "qrcode": {"detected": False, "payload": None},
                            "nanotrack": track_data,
                        }
                    )

            elif self.state == VisionState.IDLE:
                # 在空闲状态下，执行所有启用的检测
                yolo_data = self._detect_yolo(img)
                blob_data = (
                    self._detect_blobs(img)
                    if self.blob_detection_enabled
                    else {"detected": False}
                )
                apriltag_data = self._detect_apriltags(img)
                qrcode_data = (  # <--- 新增：调用二维码检测
                    self._detect_qrcodes(img)
                    if self.qrcode_detection_enabled
                    else {"detected": False, "payload": None}
                )
                with self.lock:
                    self.latest_data.update(
                        {
                            "yolo_objects": yolo_data,
                            "color_block": blob_data,
                            "apriltag": apriltag_data,
                            "qrcode": qrcode_data,
                            "nanotrack": {"detected": False, "status": "IDLE"},
                        }
                    )

            # 保存图像并更新JPEG数据
            err = img.save(TEMP_FRAME_PATH, quality=90)
            jpeg_bytes = None
            if err == 0:
                with open(TEMP_FRAME_PATH, "rb") as f:
                    jpeg_bytes = f.read()
            with self.lock:
                self.latest_jpeg = jpeg_bytes
                # --- [新增] 将最终图像显示在本地屏幕上 ---
            if self.disp:
                try:
                    self.disp.show(img)
                except Exception as e:
                    print(f"!!! Failed to show image on local display: {e}")
                    self.disp = None  # 出错一次后不再尝试，防止刷屏
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
                # <--- 核心修改：在追踪数据中添加坐标信息 ---
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
            print(f"!!! Tracking failed (likely format mismatch): {e}")
            self.stop_tracking()
        return {"detected": False, "status": "LOST"}

    def _detect_qrcodes(self, img):
        qrcodes = img.find_qrcodes()
        if not qrcodes:
            return {"detected": False, "payload": None}

        qr = qrcodes[0]  # 只处理第一个
        # 绘制边框
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
        show_info = None  # 用于发送到前端的详细信息
        display_str = ""  # 用于在本地屏幕上显示的简短信息

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
                # 如果不是已知编号的JSON，美化打印
                show_info = "\n".join(f"{k}: {v}" for k, v in data.items())
                key, value = next(iter(data.items()))
                display_str = f"{key}: {value}"
        except Exception:
            # 如果不是JSON，则作为普通字符串处理
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
        status = "enabled" if self.blob_detection_enabled else "disabled"
        print(f"Color block detection has been {status}.")
        return self.blob_detection_enabled

    # <--- 新增：设置二维码检测状态的函数 ---
    def set_qrcode_detection_status(self, enabled):
        self.qrcode_detection_enabled = bool(enabled)
        status = "enabled" if self.qrcode_detection_enabled else "disabled"
        print(f"QRCode detection has been {status}.")
        return self.qrcode_detection_enabled

    def _detect_yolo(self, img):
        if not self.detector:
            return {"detected": False, "objects": []}
        try:
            objs = self.detector.detect(
                img, conf_th=CONF_THRESHOLD, iou_th=IOU_THRESHOLD
            )
        except Exception:
            return {"detected": False, "objects": []}

        formatted_objects = []
        for obj in objs:
            center_x, center_y = obj.x + obj.w // 2, obj.y + obj.h // 2
            offset_x = center_x - self.center_x
            offset_y = center_y - self.center_y
            img.draw_rect(obj.x, obj.y, obj.w, obj.h, image.COLOR_RED, 2)
            msg = f"{self.detector.labels[obj.class_id]}: {obj.score:.2f}"
            img.draw_string(obj.x, obj.y - 15, msg, image.COLOR_RED)
            img.draw_cross(center_x, center_y, image.COLOR_GREEN)
            formatted_objects.append(
                {
                    "x": int(obj.x),
                    "y": int(obj.y),
                    "w": int(obj.w),
                    "h": int(obj.h),
                    "center_x": int(center_x),
                    "center_y": int(center_y),
                    "offset_x": int(offset_x),
                    "offset_y": int(offset_y),
                    "label": str(self.detector.labels[obj.class_id]),
                    "score": float(obj.score),
                    "area": int(obj.w * obj.h),
                }
            )
        if formatted_objects:
            formatted_objects.sort(key=lambda o: o["area"], reverse=True)
            primary_target = formatted_objects[0].copy()
            return {
                "detected": True,
                "objects": formatted_objects,
                "primary_target": primary_target,
            }
        return {"detected": False, "objects": []}

    def _detect_blobs(self, img):
        blobs = img.find_blobs(
            self.TH_RED, pixels_threshold=self.BLOB_PIXELS_THRESHOLD, merge=True
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
