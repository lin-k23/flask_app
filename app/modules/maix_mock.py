import numpy as np
from PIL import Image, ImageDraw
import time
import math

# --- 模拟 MaixPy 的数据结构 ---


class MockBlob:
    """模拟 find_blobs 返回的色块对象。"""

    def __init__(self, x, y, w, h):
        self._cx = x
        self._cy = y
        self._w = w
        self._h = h

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
        self._id = tag_id
        self._cx = x
        self._cy = y
        self._corners = corners

    def id(self):
        return self._id

    def cx(self):
        return self._cx

    def cy(self):
        return self._cy

    def corners(self):
        return self._corners


# --- 模拟 MaixPy 的核心类 ---


class MockImage:
    """
    模拟的 Image 类，使用Pillow在后台创建一个真实图像，
    并模拟绘制、查找对象等方法。
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.img = Image.new("RGB", (width, height), color="darkgray")
        self.draw = ImageDraw.Draw(self.img)
        self.COLOR_GREEN = "green"
        self.COLOR_RED = "red"
        self.ApriltagFamilies = None  # 只是为了让代码不报错

        # 模拟动态物体的位置
        self.blob_center = (width / 2, height / 2)
        self.tag_center = (width / 4, height / 4)

    def _update_object_positions(self):
        """让模拟的物体动起来"""
        t = time.time()
        # 色块做圆周运动
        self.blob_center = (
            self.width / 2 + math.sin(t) * 50,
            self.height / 2 + math.cos(t) * 50,
        )
        # AprilTag做斜线往复运动
        self.tag_center = (
            self.width / 2 + math.sin(t * 0.7) * 80,
            self.height / 2 - math.cos(t * 0.7) * 60,
        )

    def find_blobs(self, thresholds, pixels_threshold=100, merge=True):
        """模拟检测色块，总是返回一个在动态位置的色块。"""
        x, y = self.blob_center
        return [MockBlob(int(x), int(y), 30, 30)]

    def find_apriltags(self, families=None):
        """模拟检测AprilTag，总是返回一个在动态位置的Tag。"""
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

    def save(self, path, quality=90):
        """使用Pillow来保存图像。"""
        self.img.save(path, "JPEG", quality=quality)
        return 0  # 返回0表示成功


class MockCamera:
    """模拟的 Camera 类。"""

    def __init__(self, width=320, height=240):
        self.width = width
        self.height = height
        self.mock_image = MockImage(width, height)
        print("--- [DEBUG] Using MOCK MaixPy Camera ---")

    def read(self):
        """每次读取都返回一个更新了动态物体位置的新图像。"""
        # 每次读取前，都重新生成背景和动态物体
        self.mock_image.img.paste("darkgray", (0, 0, self.width, self.height))
        self.mock_image._update_object_positions()

        # 在图像上绘制模拟的物体，方便调试
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


# --- 模拟 maix 模块结构 ---


class Maix:
    def __init__(self):
        self.camera = self
        self.image = self

    def Camera(self, width, height):
        return MockCamera(width, height)

    @property
    def ApriltagFamilies(self):
        class Families:
            TAG36H11 = "TAG36H11"

        return Families


class MockUART:
    """模拟的 UART 类。"""

    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        print(
            f"--- [DEBUG] MOCK UART initialized on port {port} at {baudrate} baud. ---"
        )

    def read(self):
        # 模拟偶尔接收到来自机械臂的消息
        if time.time() % 15 < 1:  # 每15秒模拟一次接收
            return b"ARM_STATUS: MOCK OK\n"
        return None

    def write_str(self, s):
        print(f"--- [DEBUG] MOCK UART Write Str: {s.strip()}")
        return len(s)

    def write(self, b):
        print(f"--- [DEBUG] MOCK UART Write Bytes: {b}")
        return len(b)


# --- Modify the Maix class to include UART ---
# Find the existing `class Maix:` and add the UART method to it.


class Maix:
    COLOR_GREEN = "green"
    COLOR_RED = "red"

    def __init__(self):
        self.camera = self
        self.image = self
        self.uart = self  # Add this line

    def Camera(self, width, height):
        return MockCamera(width, height)

    def UART(self, port, baudrate):  # Add this method
        return MockUART(port, baudrate)

    @property
    def ApriltagFamilies(self):
        class Families:
            TAG36H11 = "TAG36H11"

        return Families


# --- Modify the exports at the very end of the file ---
# Find the existing exports and add `uart`

# 导出一个模拟的实例
camera = Maix()
image = Maix()
uart = Maix()
