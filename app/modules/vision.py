# app/modules/vision.py
import threading
import time
import tempfile
import os
import math

try:
    from maix import camera, image, nn
except (ImportError, ModuleNotFoundError):
    print("!!! maix library not found, switching to MOCK mode for development. !!!")
    from .maix_mock import camera, image, nn

MODEL_PATH = "model_234836.mud"
FALLBACK_MODEL_PATH = "/root/models/maixhub/234836/model_234836.mud"
CONF_THRESHOLD = 0.5
IOU_THRESHOLD = 0.45
TEMP_FRAME_PATH = os.path.join(tempfile.gettempdir(), "vision_frame.jpg")


class VisionProcessor:
    def __init__(self, width=320, height=240):
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

        self.center_x = width // 2
        self.center_y = height // 2
        self.blob_detection_enabled = True
        self.TH_RED = [[0, 80, 40, 80, 10, 80]]
        self.BLOB_PIXELS_THRESHOLD = 150
        self.APRILTAG_FAMILIES = image.ApriltagFamilies.TAG36H11
        self.APRILTAG_DISTANCE_FACTOR_K = 20.0

        self.latest_jpeg = None
        self.latest_data = {
            "color_block": {"detected": False},
            "apriltag": {"detected": False},
            "yolo_objects": {"detected": False, "objects": []},
        }
        self.lock = threading.Lock()
        self.stopped = False
        self.thread = threading.Thread(target=self.run, daemon=True)

    def set_blob_detection_status(self, enabled):
        self.blob_detection_enabled = bool(enabled)
        status = "enabled" if self.blob_detection_enabled else "disabled"
        print(f"Color block detection has been {status}.")
        return self.blob_detection_enabled

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

            yolo_data = self._detect_yolo(img)
            blob_data = (
                self._detect_blobs(img)
                if self.blob_detection_enabled
                else {"detected": False}
            )
            apriltag_data = self._detect_apriltags(img)

            err = img.save(TEMP_FRAME_PATH, quality=90)
            jpeg_bytes = None
            if err == 0:
                with open(TEMP_FRAME_PATH, "rb") as f:
                    jpeg_bytes = f.read()

            with self.lock:
                self.latest_jpeg = jpeg_bytes
                self.latest_data["color_block"] = blob_data
                self.latest_data["apriltag"] = apriltag_data
                self.latest_data["yolo_objects"] = yolo_data
            time.sleep(0.05)

    def _detect_yolo(self, img):
        if not self.detector:
            return {"detected": False, "objects": []}
        objs = self.detector.detect(img, conf_th=CONF_THRESHOLD, iou_th=IOU_THRESHOLD)
        formatted_objects = []
        for obj in objs:
            center_x = obj.x + obj.w // 2
            center_y = obj.y + obj.h // 2
            offset_x = center_x - self.center_x
            offset_y = center_y - self.center_y
            img.draw_rect(obj.x, obj.y, obj.w, obj.h, image.COLOR_RED, 2)
            msg = f"{self.detector.labels[obj.class_id]}: {obj.score:.2f}"
            img.draw_string(obj.x, obj.y - 15, msg, image.COLOR_RED)
            img.draw_cross(center_x, center_y, image.COLOR_GREEN)

            # --- [核心修正] 强制转换所有数值类型 ---
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
            return {
                "detected": True,
                "objects": formatted_objects,
                "primary_target": formatted_objects[0],
            }
        return {"detected": False, "objects": []}

    def _detect_blobs(self, img):
        blobs = img.find_blobs(
            self.TH_RED, pixels_threshold=self.BLOB_PIXELS_THRESHOLD, merge=True
        )
        if blobs:
            largest_blob = max(blobs, key=lambda b: b.area())
            corners = largest_blob.mini_corners()
            rotation_rad, rotation_deg = calculate_angle_from_corners(corners)
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
            return self.latest_data


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
