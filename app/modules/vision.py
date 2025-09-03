import threading
import time
from maix import camera, image

# 定义一个常量来存储临时文件路径，使用/tmp通常会写入RAM
TEMP_FRAME_PATH = "/tmp/vision_frame.jpg"


class VisionProcessor:
    """
    在后台线程中处理所有摄像头和视觉检测任务的类。
    """

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
        """后台线程的主循环函数"""
        while not self.stopped:
            img = self.cam.read()
            if not img:
                time.sleep(0.01)
                continue

            # 执行视觉检测任务
            blob_data = self._detect_blobs(img)
            apriltag_data = self._detect_apriltags(img)

            # --- [核心修正] ---
            # 1. 将处理后的图像（带有绘图）保存到临时文件
            err = img.save(TEMP_FRAME_PATH, quality=90)
            jpeg_bytes = None
            if err == 0:
                # 2. 从该文件中立即读回字节数据
                with open(TEMP_FRAME_PATH, "rb") as f:
                    jpeg_bytes = f.read()
            else:
                print(f"Error saving frame in vision thread: {err}")
            # --- [修正结束] ---

            # 使用锁来安全地更新共享数据
            with self.lock:
                self.latest_jpeg = jpeg_bytes  # 确保这里存储的是字节
                self.latest_data["color_block"] = blob_data
                self.latest_data["apriltag"] = apriltag_data

            time.sleep(0.05)

    def _detect_blobs(self, img):
        """检测色块并在图像上绘制，返回结构化数据"""
        blobs = img.find_blobs(
            self.TH_RED, pixels_threshold=self.BLOB_PIXELS_THRESHOLD, merge=True
        )
        if blobs:
            largest_blob = max(blobs, key=lambda b: b.area())
            # 绘制紧密贴合的旋转外框
            corners = largest_blob.mini_corners()
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                img.draw_line(p1[0], p1[1], p2[0], p2[1], image.COLOR_GREEN, 2)
            img.draw_cross(
                largest_blob.cx(), largest_blob.cy(), color=image.COLOR_RED, size=10
            )
            return {
                "x": largest_blob.cx(),
                "y": largest_blob.cy(),
                "w": largest_blob.w(),
                "h": largest_blob.h(),
                "detected": True,
            }
        return {"detected": False}

    def _detect_apriltags(self, img):
        """检测AprilTag并在图像上绘制，返回结构化数据"""
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

            return {"id": tag.id(), "x": cx, "y": cy, "detected": True}
        return {"detected": False}

    def get_latest_frame(self):
        """线程安全地获取最新的JPEG帧"""
        with self.lock:
            return self.latest_jpeg

    def get_latest_data(self):
        """线程安全地获取最新的检测数据"""
        with self.lock:
            return self.latest_data
