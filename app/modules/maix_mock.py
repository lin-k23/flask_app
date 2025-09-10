# app/modules/maix_mock.py
import numpy as np
from PIL import Image, ImageDraw
import time
import math
import collections
import threading


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
    # ... (这个类的内容保持不变) ...
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
        return []

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
        print("--- [MOCK] Using MOCK MaixPy Camera ---")

    def read(self):
        self.mock_image.img.paste("darkgray", (0, 0, self.width, self.height))
        self.mock_image._update_object_positions()  # 确保模拟对象会动
        return self.mock_image

    def close(self):
        print("--- [MOCK] MOCK MaixPy Camera closed. ---")


# --- [核心修改] 更新 MockUART 类以模拟协同任务 ---
class MockUART:
    def __init__(self, port, baudrate):
        self.port, self.baudrate = port, baudrate
        self.read_buffer = collections.deque(maxlen=10)
        self.write_log = []
        self.lock = threading.Lock()

        print(
            f"--- [MOCK] MOCK UART initialized on port {port} at {baudrate} baud. ---"
        )

        # 如果是小车UART，则自动开始任务流程
        if self.port == "/dev/ttyS2":
            print(
                f"--- [MOCK] Car UART ({self.port}) will start task 1 in 5 seconds. ---"
            )
            threading.Timer(5.0, self._add_to_read_buffer, args=["task1_start"]).start()

    def _add_to_read_buffer(self, message):
        """线程安全地向读取缓冲区添加消息"""
        with self.lock:
            print(f"--- [MOCK] Hardware on {self.port} sends: '{message}' ---")
            self.read_buffer.append(message.encode("utf-8"))

    def read(self):
        """线程安全地从读取缓冲区读取消息"""
        with self.lock:
            if self.read_buffer:
                return self.read_buffer.popleft()
        return None

    def write_str(self, s):
        """模拟发送字符串指令"""
        command = s.strip()
        self.write_log.append(command)
        print(f"--- [MOCK] Controller sends to {self.port}: '{command}' ---")

        # 模拟机械臂 (ttyS0) 的响应
        if self.port == "/dev/ttyS0":
            if command == "arm_task1":
                # 模拟3秒后完成任务
                threading.Timer(
                    3.0, self._add_to_read_buffer, args=["arm_task1_end"]
                ).start()
            elif command == "arm_task2":
                # 模拟3秒后完成任务
                threading.Timer(
                    3.0, self._add_to_read_buffer, args=["arm_task2_end"]
                ).start()

        # 模拟小车 (ttyS2) 的响应
        elif self.port == "/dev/ttyS2":
            if "##task1_end" in command:  # 检查打包后的命令
                # 模拟3秒后到达下一个站点
                threading.Timer(
                    3.0, self._add_to_read_buffer, args=["task2_start"]
                ).start()
            elif "##task2_end" in command:
                print(
                    f"--- [MOCK] Car on {self.port} received final task end. Cycle complete. ---"
                )
                # 可以选择在这里重启循环
                # threading.Timer(5.0, self._add_to_read_buffer, args=["task1_start"]).start()

        return len(s)

    def write(self, b):
        """模拟发送字节指令（例如协议打包的数据）"""
        self.write_log.append(b.hex().upper())
        print(
            f"--- [MOCK] Controller sends to {self.port} (bytes): {b.hex().upper()} ---"
        )
        return len(b)


# ... (MockDisplay, MockNN, MockTrackResult, MockNanoTrack 保持不变) ...
class MockDisplay:
    def __init__(self):
        print("--- [MOCK] Display instantiated. ---")

    def show(self, img):
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
    COLOR_GREEN = "green"
    COLOR_RED = "red"

    def __init__(self):
        self.camera = self
        self.image = self
        self.uart = self
        self.nn = self
        self.display = self

    def Camera(self, width, height):
        return MockCamera(width, height)

    def UART(self, port, baudrate):
        return MockUART(port, baudrate)

    def Display(self):
        return MockDisplay()

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
display = Maix()


# --- [新增] 模拟 Pinmap 类 ---
class MockPinmap:
    def set_pin_function(self, pin, func):
        print(f"--- [MOCK] Setting pin {pin} to function {func} ---")


pinmap = MockPinmap()
