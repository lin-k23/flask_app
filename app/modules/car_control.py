# app/modules/car_control.py
import threading
import time
import collections

try:
    from maix import uart, pinmap  # <--- 1. 导入 pinmap 库
except (ImportError, ModuleNotFoundError):
    print("!!! maix.uart/pinmap not found for car, switching to MOCK mode. !!!")

    # 在模拟模式下，创建一个空的 pinmap 对象，避免出错
    class MockPinmap:
        def set_pin_function(self, pin, func):
            print(f"--- [MOCK] Setting pin {pin} to function {func} ---")

    pinmap = MockPinmap()
    from .maix_mock import uart


class CarController:
    def __init__(self, port="/dev/ttyS2", baudrate=115200):
        self.serial_port = None
        self.received_log = collections.deque(maxlen=50)
        self.send_lock = threading.Lock()
        self.reader_lock = threading.Lock()

        try:
            # --- [核心修改] ---
            # 在初始化UART之前，先设置引脚功能
            print("Setting pin functions for Car UART (UART2)...")
            pinmap.set_pin_function("A28", "UART2_TX")
            pinmap.set_pin_function("A29", "UART2_RX")
            print("Pin functions for Car UART set successfully.")
            # --- [修改结束] ---

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
        """
        线程安全地向小车发送指令，并按照协议进行打包。
        """
        with self.send_lock:
            if not self.serial_port:
                print("!!! Car serial port not available.")
                return

            packet_to_send = f"##{command_string}\r\n"

            print(f"Sending to car (raw): {command_string}")
            print(f"Sending to car (packet): {repr(packet_to_send)}")

            self.serial_port.write_str(packet_to_send)
