# app/modules/maix_mock.py
import numpy as np
from PIL import Image, ImageDraw
import time
import math


# --- 模拟 MaixPy 的数据结构 (无变化) ---
class MockBlob:
    def __init__(self, x, y, w, h):
        self._cx, self._cy, self._w, self._h = x, y, w, h

    def cx(self):
        return self._cx

    def cy(self):
        return self._cy

    def w(self):
        return self._w

    def h(self):
        return self._h

    def area(self):
        return self._w * self._h

    def mini_corners(self):
        return [
            (self._cx - self._w // 2, self._cy - self._h // 2),
            (self._cx + self._w // 2, self._cy - self._h // 2),
            (self._cx + self._w // 2, self._cy + self._h // 2),
            (self._cx - self._w // 2, self._cy + self._h // 2),
        ]


class MockAprilTag:
    def __init__(self, tag_id, x, y, corners):
        self._id, self._cx, self._cy, self._corners = tag_id, x, y, corners

    def id(self):
        return self._id

    def cx(self):
        return self._cx

    def cy(self):
        return self._cy

    def corners(self):
        return self._corners

    def z_translation(self):
        return -0.5


# --- 模拟 MaixPy 的核心类 ---
class MockImage:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.img = Image.new("RGB", (width, height), color="darkgray")
        self.draw = ImageDraw.Draw(self.img)
        self.COLOR_GREEN, self.COLOR_RED = "green", "red"
        self.ApriltagFamilies = type("Families", (), {"TAG36H11": "TAG36H11"})
        self.blob_center = (width / 2, height / 2)
        self.tag_center = (width / 4, height / 4)

    def _update_object_positions(self):
        t = time.time()
        self.blob_center = (
            self.width / 2 + math.sin(t) * 50,
            self.height / 2 + math.cos(t) * 50,
        )
        self.tag_center = (
            self.width / 2 + math.sin(t * 0.7) * 80,
            self.height / 2 - math.cos(t * 0.7) * 60,
        )

    def find_blobs(self, thresholds, pixels_threshold=100, merge=True):
        return [MockBlob(int(self.blob_center[0]), int(self.blob_center[1]), 30, 30)]

    def find_apriltags(self, families=None):
        x, y = self.tag_center
        corners = [
            (x - 15, y - 15),
            (x + 15, y - 15),
            (x + 15, y + 15),
            (x - 15, y + 15),
        ]
        return [MockAprilTag(18, int(x), int(y), corners)]

    def find_qrcodes(self):
        return []  # 默认不返回二维码

    def draw_line(self, x1, y1, x2, y2, color, thickness):
        self.draw.line((x1, y1, x2, y2), fill=color, width=thickness)

    def draw_cross(self, x, y, color, size):
        half = size / 2
        self.draw.line((x - half, y, x + half, y), fill=color, width=2)
        self.draw.line((x, y - half, x, y + half), fill=color, width=2)

    def draw_string(self, x, y, text, color):
        self.draw.text((x, y), text, fill=color)

    def draw_rect(self, x, y, w, h, color, thickness):
        self.draw.rectangle((x, y, x + w, y + h), outline=color, width=thickness)

    def save(self, path, quality=90):
        self.img.save(path, "JPEG", quality=quality)
        return 0


class MockCamera:
    def __init__(self, width=320, height=240):
        self.width, self.height = width, height
        self.mock_image = MockImage(width, height)
        print("--- [DEBUG] Using MOCK MaixPy Camera ---")

    def read(self):
        self.mock_image.img.paste("darkgray", (0, 0, self.width, self.height))
        return self.mock_image

    def close(self):
        print("--- [DEBUG] MOCK MaixPy Camera closed. ---")


class MockUART:
    def __init__(self, port, baudrate):
        self.port, self.baudrate = port, baudrate
        print(
            f"--- [DEBUG] MOCK UART initialized on port {port} at {baudrate} baud. ---"
        )

    def read(self):
        return None

    def write(self, b):
        return len(b)


# --- [新增] 模拟Display类 ---
class MockDisplay:
    def __init__(self):
        print("--- [MOCK] Display instantiated. ---")

    def show(self, img):
        # 在模拟模式下，静默处理，避免刷屏
        pass


class MockNN:
    def YOLOv5(self, model):
        return None

    def NanoTrack(self, model):
        return MockNanoTrack(model)


class MockTrackResult:
    def __init__(self, x, y, w, h, score):
        self.x, self.y, self.w, self.h, self.score = x, y, w, h, score


class MockNanoTrack:
    def __init__(self, model):
        self.target = (0, 0, 0, 0)

    def init(self, img, x, y, w, h):
        self.target = (x, y, w, h)

    def track(self, img):
        return MockTrackResult(
            int(self.target[0]),
            int(self.target[1]),
            self.target[2],
            self.target[3],
            0.95,
        )


class Maix:
    def __init__(self):
        self.camera = self
        self.image = self
        self.uart = self
        self.nn = self
        self.display = self  # <-- 新增

    def Camera(self, width, height):
        return MockCamera(width, height)

    def UART(self, port, baudrate):
        return MockUART(port, baudrate)

    def Display(self):
        return MockDisplay()  # <-- 新增

    def YOLOv5(self, model):
        return MockNN().YOLOv5(model)

    def NanoTrack(self, model):
        return MockNN().NanoTrack(model)

    @property
    def ApriltagFamilies(self):
        class Families:
            TAG36H11 = "TAG36H11"

        return Families


# --- 最终导出的模拟实例 ---
camera = Maix()
image = Maix()
uart = Maix()
nn = Maix()
display = Maix()  # <-- 新增
