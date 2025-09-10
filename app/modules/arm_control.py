# app/modules/arm_control.py
import time
import threading
import collections
import struct

try:
    from maix import uart
except (ImportError, ModuleNotFoundError):
    print("!!! maix.uart not found, switching to MOCK mode for development. !!!")
    from .maix_mock import uart


class ArmController:
    def __init__(self, port="/dev/ttyS0", baudrate=115200):
        self.serial_port = None
        self.received_log = collections.deque(maxlen=50)
        self.sent_log = collections.deque(maxlen=50)
        self.lock = threading.Lock()
        self.send_lock = threading.Lock()
        self.car_controller = None
        self.vision_processor = None
        self.vision_stream_active = False
        self.vision_stream_thread = None
        self.VISION_SEND_INTERVAL = 0.5

        try:
            self.serial_port = uart.UART(port, baudrate)
            self.stopped = False
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            print(f"Arm controller initialized on {port} and reader thread started.")
        except Exception as e:
            print(f"!!! Failed to initialize arm controller on {port}: {e}")

        print("--- [TEST] Scheduling arm string test in 5 seconds. ---")
        threading.Timer(5.0, self._run_startup_test).start()

    def _run_startup_test(self):
        print("--- [TEST] Running startup test: sending string command to arm. ---")
        self.send_string_command_with_protocol("SYSTEM_CHECK")

    def send_string_command_with_protocol(self, command_string):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                payload = command_string.encode("utf-8")
                packet = self._create_packet(0x10, payload)
                log_message = f"字符串指令: {command_string}"
                return self._log_and_send(log_message, packet)
            except Exception as e:
                error_info = f"!!! 打包字符串指令 '{command_string}' 时出错: {e}"
                print(error_info)
                return error_info

    def set_car_controller(self, car_controller):
        self.car_controller = car_controller
        print("Car controller has been linked to Arm controller.")

    def set_vision_processor(self, vision_processor):
        self.vision_processor = vision_processor
        print("Vision processor has been linked to Arm controller.")

    def _vision_stream_loop(self):
        while self.vision_stream_active and not self.stopped:
            if self.vision_processor:
                latest_data = self.vision_processor.get_latest_data()
                blob_data = latest_data.get("color_block")
                if blob_data and blob_data.get("detected"):
                    self.send_arm_offset_and_angle_bulk(
                        blob_data.get("offset_x", 0),
                        blob_data.get("offset_y", 0),
                        blob_data.get("angle", 0),
                        blob_data.get("color_index", 0),
                    )
                tag_data = latest_data.get("apriltag")
                if tag_data and tag_data.get("detected"):
                    self.send_april_tag_offset(
                        tag_data.get("offset_x", 0),
                        tag_data.get("offset_y", 0),
                        tag_data.get("distance", 0),
                    )
            time.sleep(self.VISION_SEND_INTERVAL)

    def start_vision_streams(self):
        if not self.vision_stream_active:
            self.vision_stream_active = True
            self.vision_stream_thread = threading.Thread(
                target=self._vision_stream_loop, daemon=True
            )
            self.vision_stream_thread.start()
            print("Vision streams for arm have been started.")

    def stop_vision_streams(self):
        if self.vision_stream_active:
            self.vision_stream_active = False
            if self.vision_stream_thread and self.vision_stream_thread.is_alive():
                self.vision_stream_thread.join()
            print("Vision streams for arm have been stopped.")

    def get_vision_stream_status(self):
        return {"is_active": self.vision_stream_active}

    def send_task_command(self, command_string):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                payload = command_string.encode("utf-8")
                packet = self._create_packet(0x10, payload)
                log_message = f"任务指令: {command_string}"
                self._log_and_send(log_message, packet)
                self.start_vision_streams()
                return log_message
            except Exception as e:
                error_info = f"!!! 打包任务指令 '{command_string}' 时出错: {e}"
                print(error_info)
                return error_info

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
                            self.process_arm_message(message)
                except Exception as e:
                    print(f"Error reading from arm serial port: {e}")
                    time.sleep(1)
            time.sleep(0.01)

    def process_arm_message(self, message):
        if not self.car_controller:
            return
        task_finished = None
        if "arm_task1_end" in message:
            task_finished = "arm_task1"
        elif "arm_task2_end" in message:
            task_finished = "arm_task2"
        if task_finished:
            self.stop_vision_streams()
            self.car_controller.on_arm_task_finished(task_finished)

    def stop(self):
        self.stopped = True
        self.stop_vision_streams()
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join()

    def get_received_log(self):
        with self.lock:
            return list(self.received_log)

    def get_sent_log(self):
        return list(self.sent_log)

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

    def _log_and_send(self, log_message, packet):
        timestamped_log = f"[{time.strftime('%H:%M:%S')}] {log_message}"
        self.sent_log.append(timestamped_log)
        print(f"发送 -> {log_message} (Packet: {packet.hex().upper()})")
        if self.serial_port:
            self.serial_port.write(bytes(packet))
        return log_message

    def send_arm_offset_and_angle_bulk(self, offset_x, offset_y, angle, color_index):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                payload = struct.pack(
                    ">hhhh",
                    int(offset_x),
                    int(offset_y),
                    int(angle),
                    int(color_index),
                )
                packet = self._create_packet(0x01, payload)
                return self._log_and_send(
                    f"色块: X:{offset_x}, Y:{offset_y}, A:{int(angle)}, C:{color_index}",
                    packet,
                )
            except Exception as e:
                return f"!!! 打包色块数据时出错: {e}"

    def send_april_tag_offset(self, center_x, center_y, distance):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                payload = struct.pack(
                    ">hhh", int(center_x), int(center_y), int(distance)
                )
                packet = self._create_packet(0x02, payload)
                return self._log_and_send(
                    f"AprilTag: X:{center_x}, Y:{center_y}, D:{distance}", packet
                )
            except Exception as e:
                return f"!!! 打包AprilTag数据时出错: {e}"

    def send_pegboard_target(self, row, col, reserved=0):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                payload = struct.pack(">hhh", int(row), int(col), int(reserved))
                packet = self._create_packet(0x04, payload)
                return self._log_and_send(f"洞洞板: Row:{row}, Col:{col}", packet)
            except Exception as e:
                return f"!!! 打包洞洞板数据时出错: {e}"
