import threading
import time
import tempfile
import os
import math

try:
    from maix import camera, image
except ImportError:
    print("!!! maix library not found, switching to MOCK mode for development. !!!")
    from .maix_mock import camera, image

TEMP_FRAME_PATH = os.path.join(tempfile.gettempdir(), "vision_frame.jpg")


class VisionProcessor:
    def __init__(self, width=320, height=240):
        self.cam = camera.Camera(width, height)
        print(f"MaixPy Camera for VisionProcessor Initialized ({width}x{height})")

        self.TH_RED = [[0, 80, 40, 80, 10, 80]]
        self.BLOB_PIXELS_THRESHOLD = 150
        self.APRILTAG_FAMILIES = image.ApriltagFamilies.TAG36H11

        self.latest_jpeg = None
        self.latest_data = {
            "color_block": {"detected": False},
            "apriltag": {"detected": False},
        }
        self.lock = threading.Lock()

        self.stopped = False
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()
        print("VisionProcessor thread started.")

    def stop(self):
        self.stopped = True
        if self.thread.is_alive():
            self.thread.join()
        if hasattr(self, "cam"):
            self.cam.close()
        print("VisionProcessor thread stopped and camera released.")

    def run(self):
        # ... (run 方法保持不变) ...
        while not self.stopped:
            img = self.cam.read()
            if not img:
                time.sleep(0.01)
                continue

            blob_data = self._detect_blobs(img)
            apriltag_data = self._detect_apriltags(img)

            err = img.save(TEMP_FRAME_PATH, quality=90)
            jpeg_bytes = None
            if err == 0:
                with open(TEMP_FRAME_PATH, "rb") as f:
                    jpeg_bytes = f.read()
            else:
                print(f"Error saving frame in vision thread: {err}")

            with self.lock:
                self.latest_jpeg = jpeg_bytes
                self.latest_data["color_block"] = blob_data
                self.latest_data["apriltag"] = apriltag_data

            time.sleep(0.05)

    def _detect_blobs(self, img):
        blobs = img.find_blobs(
            self.TH_RED, pixels_threshold=self.BLOB_PIXELS_THRESHOLD, merge=True
        )
        if blobs:
            largest_blob = max(blobs, key=lambda b: b.area())
            corners = largest_blob.mini_corners()
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                img.draw_line(p1[0], p1[1], p2[0], p2[1], image.COLOR_GREEN, 2)

            # --- [核心修改] 调用函数计算角度 ---
            rotation_rad, rotation_deg = calculate_angle_from_corners(corners)

            img.draw_cross(
                largest_blob.cx(), largest_blob.cy(), color=image.COLOR_RED, size=10
            )
            # --- [核心修改] 将角度添加到返回数据中 ---
            return {
                "x": int(largest_blob.cx()),
                "y": int(largest_blob.cy()),
                "w": int(largest_blob.w()),
                "h": int(largest_blob.h()),
                "angle": rotation_deg,  # <--- 添加角度
                "detected": True,
            }
        return {"detected": False}

    def _detect_apriltags(self, img):
        tags = img.find_apriltags(families=self.APRILTAG_FAMILIES)
        if tags:
            tag = tags[0]
            corners = tag.corners()
            for i in range(4):
                img.draw_line(
                    corners[i][0],
                    corners[i][1],
                    corners[(i + 1) % 4][0],
                    corners[(i + 1) % 4][1],
                    color=image.COLOR_GREEN,
                    thickness=2,
                )

            cx, cy = tag.cx(), tag.cy()
            img.draw_cross(cx, cy, color=image.COLOR_GREEN, size=10)

            return {"id": tag.id(), "x": int(cx), "y": int(cy), "detected": True}
        return {"detected": False}

    def get_latest_frame(self):
        with self.lock:
            return self.latest_jpeg

    def get_latest_data(self):
        with self.lock:
            return self.latest_data


# --- [新功能] 将角度计算函数放在这里 ---
def calculate_angle_from_corners(corners):
    # 找到四个角点中构成最长边的两个点
    dx1, dy1 = corners[1][0] - corners[0][0], corners[1][1] - corners[0][1]
    len_sq1 = dx1**2 + dy1**2
    dx2, dy2 = corners[2][0] - corners[1][0], corners[2][1] - corners[1][1]
    len_sq2 = dx2**2 + dy2**2

    # 假设最长的边代表了物体的方向
    final_dx, final_dy = (dx1, dy1) if len_sq1 > len_sq2 else (dx2, dy2)

    # 计算角度
    rotation_rad = math.atan2(final_dy, final_dx)
    rotation_deg = math.degrees(rotation_rad)

    # (可选) 将角度标准化到0-180或0-90度范围内，取决于您的机械臂如何解释角度
    if rotation_deg < 0:
        rotation_deg += 180
    if rotation_deg > 90:
        rotation_deg -= 90

    return rotation_rad, rotation_deg
