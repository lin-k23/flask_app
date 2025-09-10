# app/modules/maix_mock.py
import numpy as np
from PIL import Image, ImageDraw
import time
import math
import collections
import threading
import struct


# ... (MockBlob, MockAprilTag, MockImage, MockCamera 的代码无变化) ...
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


class MockImage:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.img = Image.new("RGB", (width, height), color="darkgray")
        self.draw = ImageDraw.Draw(self.img)
        self.COLOR_GREEN, self.COLOR_RED = "green", "red"
        self.ApriltagFamilies = type("Families", (), {"TAG36H11": "TAG36H11"})
        self.blob_center = (width / 2, height / 2)
        self.tag_center = (width / 4, height / 4)
        self.mock_blob_color_cycle = ["blue", "yellow", "orange", "purple"]
        self.current_mock_color = "blue"

    def _update_object_positions(self):
        t = time.time()
        self.blob_center = (
            self.width / 2 + math.sin(t * 0.8) * 50,
            self.height / 2 + math.cos(t * 0.8) * 50,
        )
        self.tag_center = (
            self.width / 2 + math.sin(t * 0.7) * 80,
            self.height / 2 - math.cos(t * 0.7) * 60,
        )
        self.current_mock_color = self.mock_blob_color_cycle[
            int(t / 3) % len(self.mock_blob_color_cycle)
        ]
        x, y = self.blob_center
        self.draw.ellipse(
            (x - 15, y - 15, x + 15, y + 15), fill=self.current_mock_color
        )

    def find_blobs(self, thresholds, pixels_threshold=100, merge=True):
        requested_color = "unknown"
        first_thresh = thresholds[0][0]
        if first_thresh == [0, 80, -10, 10, -55, -30]:
            requested_color = "blue"
        elif first_thresh == [0, 80, -15, 15, 50, 80]:
            requested_color = "yellow"
        elif first_thresh == [0, 80, 40, 60, 40, 80]:
            requested_color = "orange"
        elif first_thresh == [28, 68, 12, 52, -80, -40]:
            requested_color = "purple"
        if requested_color == self.current_mock_color:
            return [
                MockBlob(int(self.blob_center[0]), int(self.blob_center[1]), 30, 30)
            ]
        return []

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
        self.mock_image._update_object_positions()
        return self.mock_image

    def close(self):
        print("--- [MOCK] MOCK MaixPy Camera closed. ---")


class MockUART:
    def __init__(self, port, baudrate):
        self.port, self.baudrate = port, baudrate
        self.read_buffer = collections.deque(maxlen=10)
        self.write_log = []
        self.lock = threading.Lock()
        print(
            f"--- [MOCK] MOCK UART initialized on port {port} at {baudrate} baud. ---"
        )

    def _add_to_read_buffer(self, message):
        with self.lock:
            print(f"--- [MOCK] Hardware on {self.port} sends: '{message}' ---")
            self.read_buffer.append(message.encode("utf-8"))

    def read(self):
        with self.lock:
            if self.read_buffer:
                return self.read_buffer.popleft()
        return None

    def write_str(self, s):
        command = s.strip()
        self.write_log.append(command)
        print(f"--- [MOCK] Controller sends to {self.port}: '{command}' ---")

        # --- [核心修改] 移除自动发送 "task2_start" 的逻辑 ---
        # The simulation flow is now controlled by separate user clicks.
        return len(s)

    def write(self, b):
        self.write_log.append(b.hex().upper())
        print(
            f"--- [MOCK] Controller sends to {self.port} (bytes): {b.hex().upper()} ---"
        )
        if self.port == "/dev/ttyS0":
            if b.startswith(b"\xaa\x55"):
                data_type = b[2]
                if data_type == 0x10:  # Task 1
                    print(
                        f"--- [MOCK] Arm received Task 1. Will send '1end' in 5 seconds. ---"
                    )
                    threading.Timer(
                        5.0, self._add_to_read_buffer, args=["1end"]
                    ).start()
                elif data_type == 0x11:  # Task 2
                    print(
                        f"--- [MOCK] Arm received Task 2. Will send '2end' in 5 seconds. ---"
                    )
                    threading.Timer(
                        5.0, self._add_to_read_buffer, args=["2end"]
                    ).start()
        return len(b)


# ... (MockDisplay, MockNN, etc. 的代码无变化) ...
class MockDisplay:
    def __init__(self):
        pass

    def show(self, img):
        pass


class MockNN:
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
    COLOR_GREEN, COLOR_RED = "green", "red"

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

    def NanoTrack(self, model):
        return MockNN().NanoTrack(model)

    @property
    def ApriltagFamilies(self):
        class Families:
            TAG36H11 = "TAG36H11"

        return Families


camera, image, uart, nn, display = Maix(), Maix(), Maix(), Maix(), Maix()


class MockPinmap:
    def set_pin_function(self, pin, func):
        pass


pinmap = MockPinmap()
