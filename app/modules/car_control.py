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
        self.arm_controller = None

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

    # --- [新增] 接收 arm_controller 实例的方法 ---
    def set_arm_controller(self, arm_controller):
        self.arm_controller = arm_controller
        print("Arm controller has been linked to Car controller.")

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

    # --- [核心修改] 任务处理逻辑 ---
    def process_task_message(self, message):
        print(f"Processing task message: {message}, current stage: {self.task_stage}")

        # 检查 arm_controller 是否已连接
        if not self.arm_controller:
            print("!!! Arm controller not linked, cannot start协同task.")
            return

        if "task1_start" in message and self.task_stage == 1:
            print("Received task1_start from car. Commanding arm to start arm_task1.")
            # 直接命令机械臂开始任务1
            self.arm_controller.send_task_command("arm_task1")

        elif "task2_start" in message and self.task_stage == 2:
            print("Received task2_start from car. Commanding arm to start arm_task2.")
            # 直接命令机械臂开始任务2
            self.arm_controller.send_task_command("arm_task2")

    # --- [新增] 供机械臂调用的回调函数 ---
    def on_arm_task_finished(self, arm_task_name):
        """当机械臂完成任务后，此方法被 ArmController 调用"""
        print(f"Received notification that arm finished '{arm_task_name}'.")
        if arm_task_name == "arm_task1" and self.task_stage == 1:
            print("Arm task 1 finished. Sending task1_end to car.")
            self.send_command("task1_end")
            self.task_stage = 2  # 更新状态，准备接收 task2_start

        elif arm_task_name == "arm_task2" and self.task_stage == 2:
            print("Arm task 2 finished. Sending task2_end to car.")
            self.send_command("task2_end")
            self.task_stage = 1  # 重置任务状态，准备下一轮
            print("Task sequence complete. Resetting stage to 1.")

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
