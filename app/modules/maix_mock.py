# app/modules/maix_mock.py
import numpy as np
from PIL import Image, ImageDraw
import time
import math

# --- 模拟 MaixPy 的数据结构 ---


class MockBlob:
    """模拟 find_blobs 返回的色块对象。"""

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
    """模拟 find_apriltags 返回的AprilTag对象。"""

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
        return -0.5  # <-- [FIX 1] 添加缺失的方法


# --- 模拟 MaixPy 的核心类 ---


class MockImage:
    """模拟的 Image 类，使用Pillow在后台创建图像。"""

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
        x, y = self.blob_center
        return [MockBlob(int(x), int(y), 30, 30)]

    def find_apriltags(self, families=None):
        x, y = self.tag_center
        corners = [
            (x - 15, y - 15),
            (x + 15, y - 15),
            (x + 15, y + 15),
            (x - 15, y + 15),
        ]
        return [MockAprilTag(18, int(x), int(y), corners)]

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
    """模拟的 Camera 类。"""

    def __init__(self, width=320, height=240):
        self.width, self.height = width, height
        self.mock_image = MockImage(width, height)
        print("--- [DEBUG] Using MOCK MaixPy Camera ---")

    def read(self):
        self.mock_image.img.paste("darkgray", (0, 0, self.width, self.height))
        self.mock_image._update_object_positions()
        bx, by = self.mock_image.blob_center
        self.mock_image.draw.rectangle(
            (bx - 15, by - 15, bx + 15, by + 15), fill="red", outline="white"
        )
        tx, ty = self.mock_image.tag_center
        self.mock_image.draw.rectangle(
            (tx - 15, ty - 15, tx + 15, ty + 15), fill="blue", outline="white"
        )
        self.mock_image.draw.text((tx - 5, ty - 5), "18", fill="white")
        return self.mock_image

    def close(self):
        print("--- [DEBUG] MOCK MaixPy Camera closed. ---")


class MockUART:
    """模拟的 UART 类。"""

    def __init__(self, port, baudrate):
        self.port, self.baudrate = port, baudrate
        print(
            f"--- [DEBUG] MOCK UART initialized on port {port} at {baudrate} baud. ---"
        )

    def read(self):
        if time.time() % 15 < 1:
            return b"ARM_STATUS: MOCK OK\n"
        return None

    def write_str(self, s):
        print(f"--- [DEBUG] MOCK UART Write Str: {s.strip()}")
        return len(s)

    def write(self, b):
        print(f"--- [DEBUG] MOCK UART Write Bytes: {b}")
        return len(b)


# --- [FIX 2] 统一和修正模拟模块的导出结构 ---


class MockNN:
    """模拟的 NN (神经网络) 类。"""

    def YOLOv5(self, model):
        print(f"--- [MOCK] nn.YOLOv5 instantiated but will do nothing. ---")
        return None  # 返回None, vision.py中的self.detector将为None

    def NanoTrack(self, model):
        return MockNanoTrack(model)


class Maix:
    """统一的 Maix 模块模拟入口。"""

    COLOR_GREEN = "green"
    COLOR_RED = "red"

    def __init__(self):
        # 让 camera, image, uart, nn 都可以通过 Maix() 实例访问到
        self.camera = self
        self.image = self
        self.uart = self
        self.nn = self

    def Camera(self, width, height):
        return MockCamera(width, height)

    def UART(self, port, baudrate):
        return MockUART(port, baudrate)

    def YOLOv5(self, model):
        return MockNN().YOLOv5(model)

    def NanoTrack(self, model):
        return MockNN().NanoTrack(model)

    @property
    def ApriltagFamilies(self):
        class Families:
            TAG36H11 = "TAG36H11"

        return Families


class MockTrackResult:
    """模拟 tracker.track 返回的结果"""

    def __init__(self, x, y, w, h, score):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.score = score


class MockNanoTrack:
    """模拟的 NanoTrack 类"""

    def __init__(self, model):
        self.target = (0, 0, 0, 0)
        print(f"--- [MOCK] nn.NanoTrack instantiated with model {model}. ---")

    def init(self, img, x, y, w, h):
        self.target = (x, y, w, h)
        print(f"--- [MOCK] NanoTrack initialized with rect: {(x, y, w, h)}")

    def track(self, img):
        # 模拟目标轻微移动
        x, y, w, h = self.target
        new_x = x + math.sin(time.time() * 2) * 5
        new_y = y + math.cos(time.time() * 2) * 5
        self.target = (new_x, new_y, w, h)
        return MockTrackResult(int(new_x), int(new_y), w, h, 0.95)


# --- 最终导出的模拟实例 ---
# vision.py 会从这个文件导入 camera, image, 和 nn
camera = Maix()
image = Maix()
uart = Maix()
nn = Maix()
