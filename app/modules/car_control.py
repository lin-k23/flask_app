# app/modules/car_control.py
import threading
import time
import collections

try:
    from maix import uart, pinmap
except (ImportError, ModuleNotFoundError):
    print("!!! maix.uart/pinmap not found for car, switching to MOCK mode. !!!")

    class MockPinmap:
        def set_pin_function(self, pin, func):
            print(f"--- [MOCK] Setting pin {pin} to function {func} ---")

    pinmap = MockPinmap()
    from .maix_mock import uart


class CarController:
    def __init__(self, port="/dev/ttyS2", baudrate=115200):
        self.serial_port = None
        self.received_log = collections.deque(maxlen=50)
        # --- [新增] 创建一个用于存储发送日志的队列 ---
        self.sent_log = collections.deque(maxlen=50)
        self.send_lock = threading.Lock()
        self.reader_lock = threading.Lock()

        self.task_stage = 1

        try:
            print("Setting pin functions for Car UART (UART2)...")
            pinmap.set_pin_function("A28", "UART2_TX")
            pinmap.set_pin_function("A29", "UART2_RX")
            print("Pin functions for Car UART set successfully.")

            self.serial_port = uart.UART(port, baudrate)
            self.stopped = False
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            print(f"Car controller initialized on {port} and reader thread started.")
        except Exception as e:
            print(f"!!! Failed to initialize car controller on {port}: {e}")

    def _read_loop(self):
        while not self.stopped:
            if self.serial_port:
                try:
                    data = self.serial_port.read()
                    if data:
                        message = data.decode("utf-8", errors="ignore").strip()
                        if message:
                            with self.reader_lock:
                                self.received_log.append(
                                    f"[{time.strftime('%H:%M:%S')}] {message}"
                                )
                            self.process_task_message(message)
                except Exception as e:
                    print(f"Error reading from car serial port: {e}")
                    time.sleep(1)
            time.sleep(0.01)

    def process_task_message(self, message):
        print(f"Processing task message: {message}, current stage: {self.task_stage}")
        if "task1_start" in message and self.task_stage == 1:
            print("Received task1_start. Simulating arm task for 5 seconds...")

            def task_1_delay():
                print("Simulation finished. Sending task1_end to car.")
                self.send_command("task1_end")
                self.task_stage = 2

            self.send_command("Test for task1_start received")
            timer = threading.Timer(5.0, task_1_delay)
            timer.start()
        elif "task2_start" in message and self.task_stage == 2:
            print("Received task2_start. Simulating arm task for 5 seconds...")

            def task_2_delay():
                print("Simulation finished. Sending task2_end to car.")
                self.send_command("task2_end")
                self.task_stage = 1
                print("Task stage has been reset to 1.")

            timer = threading.Timer(5.0, task_2_delay)
            timer.start()

    def stop_thread(self):
        self.stopped = True
        if self.reader_thread.is_alive():
            self.reader_thread.join()

    def get_received_log(self):
        with self.reader_lock:
            return list(self.received_log)

    # --- [新增] 添加一个获取发送日志的函数 ---
    def get_sent_log(self):
        # 这个函数不需要锁，因为deque的append是线程安全的
        return list(self.sent_log)

    def send_command(self, command_string):
        with self.send_lock:
            if not self.serial_port:
                print("!!! Car serial port not available.")
                return

            packet_to_send = f"##{command_string}\r\n"

            # --- [核心修改] 将发送的命令记录到日志中 ---
            log_message = f"[{time.strftime('%H:%M:%S')}] {command_string}"
            self.sent_log.append(log_message)
            # --- [修改结束] ---

            print(f"Sending to car (raw): {command_string}")
            print(f"Sending to car (packet): {repr(packet_to_send)}")
            self.serial_port.write_str(packet_to_send)
