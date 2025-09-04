import time
import math
import threading
import collections
import struct

try:
    from maix import uart
except (ImportError, ModuleNotFoundError):
    print("!!! maix.uart not found, switching to MOCK mode for development. !!!")
    from .maix_mock import uart


class ArmController:
    """
    封装了与机械臂通信和控制所有逻辑的类。
    """

    def __init__(self, port="/dev/ttyS0", baudrate=115200):
        self.serial_port = None
        self.received_log = collections.deque(maxlen=50)
        self.lock = threading.Lock()
        self.send_lock = threading.Lock()

        try:
            self.serial_port = uart.UART(port, baudrate)
            self.stopped = False
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            print(f"Arm controller initialized on {port} and reader thread started.")
        except Exception as e:
            print(f"!!! Failed to initialize arm controller on {port}: {e}")

    def _read_loop(self):
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
                    time.sleep(1)
            time.sleep(0.01)

    def stop(self):
        self.stopped = True
        if self.reader_thread.is_alive():
            self.reader_thread.join()

    def get_received_log(self):
        with self.lock:
            return list(self.received_log)

    def _create_packet(self, data_type, payload):
        length = len(payload)
        header = bytearray([0xAA, 0x55])
        dt_byte = data_type.to_bytes(1, "big")
        length_byte = length.to_bytes(1, "big")
        checksum_val = (data_type + length + sum(payload)) & 0xFF
        checksum_byte = checksum_val.to_bytes(1, "big")
        tail = bytearray([0x0D, 0x0A])
        packet = header + dt_byte + length_byte + payload + checksum_byte + tail
        return packet

    def send_arm_offset_and_angle_bulk(self, offset_x, offset_y, angle):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"

            angle_to_send = int(angle)

            try:
                payload = struct.pack(
                    ">hhh", int(offset_x), int(offset_y), angle_to_send
                )
                packet = self._create_packet(0x01, payload)
                self.serial_port.write(bytes(packet))
                # --- [核心修改] 返回详细的发送信息 ---
                sent_info = f"色块: {packet.hex().upper()}"
                print(f"发送 -> {sent_info}")
                return sent_info
            except Exception as e:
                error_info = f"!!! 打包色块数据时出错: {e}"
                print(error_info)
                return error_info

    def send_april_tag_offset(self, center_x, center_y, distance):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"

            try:
                payload = struct.pack(
                    ">hhh", int(center_x), int(center_y), int(distance)
                )
                packet = self._create_packet(0x02, payload)
                self.serial_port.write(bytes(packet))
                # --- [核心修改] 返回详细的发送信息 ---
                sent_info = f"AprilTag: {packet.hex().upper()}"
                print(f"发送 -> {sent_info}")
                return sent_info
            except Exception as e:
                error_info = f"!!! 打包AprilTag数据时出错: {e}"
                print(error_info)
                return error_info

    def handle_command(self, command_string):
        print(
            f"警告：尝试通过已禁用的 handle_command 发送指令 '{command_string}'。操作已取消。"
        )
        return "警告: 自定义字符串指令已禁用"
