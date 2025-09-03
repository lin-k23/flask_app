# app/modules/car_control.py
import threading
import time
import collections

try:
    from maix import uart
except (ImportError, ModuleNotFoundError):
    print("!!! maix.uart not found for car, switching to MOCK mode. !!!")
    from .maix_mock import uart


class CarController:
    def __init__(self, port="/dev/ttyS2", baudrate=115200):
        self.serial_port = None
        self.received_log = collections.deque(maxlen=50)  # 存储日志
        self.send_lock = threading.Lock()  # 发送锁，防止冲突
        self.reader_lock = threading.Lock()  # 读取锁

        try:
            self.serial_port = uart.UART(port, baudrate)
            self.stopped = False
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            print(f"Car controller initialized on {port} and reader thread started.")
        except Exception as e:
            print(f"!!! Failed to initialize car controller on {port}: {e}")

    def _read_loop(self):
        """后台线程，用于持续读取小车发来的数据。"""
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
                except Exception as e:
                    print(f"Error reading from car serial port: {e}")
                    time.sleep(1)
            time.sleep(0.01)

    def stop_thread(self):
        self.stopped = True
        if self.reader_thread.is_alive():
            self.reader_thread.join()

    def get_received_log(self):
        """线程安全地获取接收到的日志。"""
        with self.reader_lock:
            return list(self.received_log)

    def send_command(self, command_string):
        """线程安全地向小车发送指令。"""
        with self.send_lock:
            if not self.serial_port:
                print("!!! Car serial port not available.")
                return
            print(f"Sending to car: {command_string}")
            self.serial_port.write_str(command_string + "\n")  # 加换行符确保接收完整
