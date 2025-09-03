import time
import math
import threading
import collections
from maix import uart


class ArmController:
    """
    封装了与机械臂通信和控制所有逻辑的类，包含后台双向通信。
    """

    def __init__(self, port="/dev/ttyS0", baudrate=115200):
        """
        初始化串口通信，并启动一个后台线程来持续接收数据。
        """
        self.serial_port = None
        self.received_log = collections.deque(maxlen=50)  # 存储最多50条收到的消息
        self.lock = threading.Lock()

        try:
            self.serial_port = uart.UART(port, baudrate)
            self.stopped = False
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            print(f"Arm controller initialized on {port} and reader thread started.")
        except Exception as e:
            print(f"!!! Failed to initialize arm controller on {port}: {e}")

    def _read_loop(self):
        """后台线程，用于持续读取串口数据。"""
        while not self.stopped:
            if self.serial_port:
                try:
                    data = self.serial_port.read()
                    if data:
                        message = data.decode("utf-8", errors="ignore").strip()
                        if message:
                            with self.lock:
                                self.received_log.append(
                                    f"[{time.strftime('%H:%M:%S')}] {message}"
                                )
                except Exception as e:
                    print(f"Error reading from arm serial port: {e}")
                    time.sleep(1)  # 发生错误时等待一下
            time.sleep(0.01)

    def stop(self):
        """停止后台线程。"""
        self.stopped = True
        if self.reader_thread.is_alive():
            self.reader_thread.join()

    def get_received_log(self):
        """线程安全地获取接收到的消息日志。"""
        with self.lock:
            return list(self.received_log)

    def send_arm_point_bulk(self, point_name, point_data):
        if not self.serial_port:
            return
        print(
            f"指令发送 -> 目标: {point_name}, 数据: {[f'{v:.2f}' for v in point_data]}"
        )
        bulk_byte_data = bytearray()
        for value in point_data:
            try:
                integer_value = int(value)
                bulk_byte_data.extend(integer_value.to_bytes(2, "big", signed=True))
            except Exception as e:
                print(f"!!! 转换数据 {value} 时出错: {e}")
                return
        self.serial_port.write_str(f"START\n")
        time.sleep(0.01)
        self.serial_port.write(bytes(bulk_byte_data))
        time.sleep(0.01)
        self.serial_port.write_str(f"END\n")
        print(f"坐标点 '{point_name}' ({len(bulk_byte_data)}字节) 发送完成。")

    def send_arm_offset_and_angle_bulk(self, offset_x, offset_y, angle):
        if not self.serial_port:
            return
        print(
            f"指令发送 -> 目标: OFFSET, 数据: X={offset_x}, Y={offset_y}, Angle={angle:.2f}"
        )
        bulk_offset_data = bytearray()
        try:
            val_x = int(offset_x)
            val_y = int(offset_y)
            val_angle = int(angle)
            bulk_offset_data.extend(val_x.to_bytes(2, "big", signed=True))
            bulk_offset_data.extend(val_y.to_bytes(2, "big", signed=True))
            bulk_offset_data.extend(val_angle.to_bytes(2, "big", signed=True))
        except Exception as e:
            print(f"!!! 处理偏移值或角度 {offset_x}, {offset_y}, {angle} 时出错: {e}")
            return
        self.serial_port.write_str(f"START_OFFSET\n")
        time.sleep(0.01)
        self.serial_port.write(bytes(bulk_offset_data))
        time.sleep(0.01)
        self.serial_port.write_str(f"END_OFFSET\n")
        print(f"偏移与角度 ({len(bulk_offset_data)}字节) 发送完成。")

    def send_april_tag_offset(self, center_x, center_y, distance):
        if not self.serial_port:
            return
        print(
            f"指令发送 -> 目标: TAG_O, 数据: X={center_x}, Y={center_y}, Distance={distance:.2f}"
        )
        bulk_offset_data = bytearray()
        try:
            val_x = int(center_x)
            val_y = int(center_y)
            val_distance = int(distance)
            bulk_offset_data.extend(val_x.to_bytes(2, "big", signed=True))
            bulk_offset_data.extend(val_y.to_bytes(2, "big", signed=True))
            bulk_offset_data.extend(val_distance.to_bytes(2, "big", signed=True))
        except Exception as e:
            print(f"!!! 处理TAG时 {center_x}, {center_y}, {distance} 时出错: {e}")
            return
        self.serial_port.write_str(f"START_TAG\n")
        time.sleep(0.01)
        self.serial_port.write(bytes(bulk_offset_data))
        time.sleep(0.01)
        self.serial_port.write_str(f"END_TAG\n")
        print(f"April TAG 坐标 ({len(bulk_offset_data)}字节) 发送完成。")

    def handle_command(self, command_string):
        """处理从API接收到的字符串指令，并直接发送。"""
        if not self.serial_port:
            return
        print(f"处理API指令: {command_string}")
        # 直接将字符串指令通过串口发送出去
        self.serial_port.write_str(command_string)


# --- 辅助函数 ---
def calculate_angle_from_corners(corners):
    # ... 此函数内容保持不变 ...
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
