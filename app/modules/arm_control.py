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
    def __init__(self, port="/dev/ttyS0", baudrate=115200, state_manager=None):
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
        self.state_manager = state_manager

        try:
            self.serial_port = uart.UART(port, baudrate)
            self.stopped = False
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            print(f"Arm controller initialized on {port} and reader thread started.")
        except Exception as e:
            print(f"!!! Failed to initialize arm controller on {port}: {e}")

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
                        tag_data.get("id", -1),  # 传入ID，如果不存在则默认为-1
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

    def send_task1_command(self):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                task1_counter = 0
                while task1_counter < 5:
                    payload = struct.pack(">h", 0)
                    packet = self._create_packet(0x10, payload)
                    log_message = "任务指令: Task 1 (0x10)"
                    self._log_and_send(log_message, packet)
                    self.start_vision_streams()
                    task1_counter = task1_counter + 1
                return log_message
            except Exception as e:
                return f"!!! 打包 Task 1 指令时出错: {e}"

    def send_task2_command(self, row, col, color_id):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                task2_counter = 0
                while task2_counter < 3:
                    payload = struct.pack(">hhh", int(row), int(col), int(color_id))
                    packet = self._create_packet(0x11, payload)
                    log_message = (
                        f"任务指令: Task 2 (0x11) -> R:{row}, C:{col}, Color:{color_id}"
                    )

                    # --- [核心修改] 发送指令后，立刻切换到自动模式 ---
                    if self.state_manager:
                        self.state_manager["status"] = "TASK_AUTO"
                        print(
                            f"--- System state changed to: {self.state_manager['status']} (triggered by Pegboard click) ---"
                        )
                    self._log_and_send(log_message, packet)
                    self.start_vision_streams()
                    task2_counter = task2_counter + 1
                return log_message
            except Exception as e:
                return f"!!! 打包 Task 2 指令时出错: {e}"

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
                    time.sleep(1)
            time.sleep(0.01)

    def process_arm_message(self, message):
        task_id_finished = None
        if "1end" in message:
            task_id_finished = 1
            print("Arm task 1 finished. Notifying car controller to send 'task1_end'.")
            self.car_controller.send_command("task1_end")

        elif "2end" in message:
            task_id_finished = 2
            print("Arm task 2 finished. Notifying car controller to send 'task2_end'.")
            self.car_controller.send_command("task2_end")

        if task_id_finished:
            if self.state_manager:
                self.state_manager["status"] = "MANUAL"
                print(
                    f"--- System state changed to: {self.state_manager['status']} (Task {task_id_finished} finished) ---"
                )
            self.stop_vision_streams()
            if self.car_controller:
                self.car_controller.update_task_stage(task_id_finished)

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

    def send_april_tag_offset(self, center_x, center_y, distance, tag_id):
        with self.send_lock:
            if not self.serial_port:
                return "错误: 串口不可用"
            try:
                payload = struct.pack(
                    ">hhhh",
                    int(center_x),
                    int(center_y),
                    int(distance),
                    int(tag_id),
                )
                packet = self._create_packet(0x02, payload)
                return self._log_and_send(
                    f"AprilTag: X:{center_x}, Y:{center_y}, D:{distance}, C:{tag_id}",
                    packet,
                )
            except Exception as e:
                return f"!!! 打包AprilTag数据时出错: {e}"
