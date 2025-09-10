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
    def __init__(self, port="/dev/ttyS2", baudrate=115200, state_manager=None):
        self.serial_port = None
        self.received_log = collections.deque(maxlen=50)
        self.sent_log = collections.deque(maxlen=50)
        self.send_lock = threading.Lock()
        self.reader_lock = threading.Lock()
        self.task_stage = 1
        self.arm_controller = None
        self.state_manager = state_manager

        try:
            pinmap.set_pin_function("A28", "UART2_TX")
            pinmap.set_pin_function("A29", "UART2_RX")
            self.serial_port = uart.UART(port, baudrate)
            self.stopped = False
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            print(f"Car controller initialized on {port} and reader thread started.")
        except Exception as e:
            print(f"!!! Failed to initialize car controller on {port}: {e}")

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
                    time.sleep(1)
            time.sleep(0.01)

    def simulate_task1_start(self):
        """Simulates receiving 'task1_start' from the car."""
        print("--- [SIMULATION] Manually triggering Task 1 start ---")
        simulated_message = f"[{time.strftime('%H:%M:%S')}] [SIMULATION] task1_start"
        with self.reader_lock:
            self.received_log.append(simulated_message)
        self.process_task_message("task1_start")
        return "Task 1 simulation started."

    def simulate_task2_start(self):
        """Simulates receiving 'task2_start' from the car."""
        if self.task_stage != 2:
            return f"Task 2 cannot be started. System is not in the correct stage (Current stage: {self.task_stage})."
        print("--- [SIMULATION] Manually triggering Task 2 start ---")
        simulated_message = f"[{time.strftime('%H:%M:%S')}] [SIMULATION] task2_start"
        with self.reader_lock:
            self.received_log.append(simulated_message)
        self.process_task_message("task2_start")
        return "Task 2 simulation started. Pegboard is now active."

    def process_task_message(self, message):
        if not self.arm_controller:
            return

        if "task1_start" in message and self.task_stage == 1:
            if self.state_manager:
                self.state_manager["status"] = "TASK_AUTO"
                print(
                    f"--- System state changed to: {self.state_manager['status']} (triggered by Task 1) ---"
                )
            print("Received task1_start. Commanding arm to start Task 1 (0x10).")
            self.arm_controller.send_task1_command()

        # --- [核心修改] 收到task2_start后，只改变状态，等待用户输入 ---
        elif "task2_start" in message and self.task_stage == 2:
            if self.state_manager:
                self.state_manager["status"] = "AWAITING_TASK2_INPUT"
                print(
                    f"--- System state changed to: {self.state_manager['status']}. Waiting for user on pegboard. ---"
                )

    def update_task_stage(self, task_id_finished):
        """Called by arm_controller to keep the car's state machine in sync."""
        print(
            f"Updating car's internal state machine after Task {task_id_finished} finished."
        )
        if task_id_finished == 1 and self.task_stage == 1:
            self.task_stage = 2
            print(f"Car task stage is now {self.task_stage}. Ready for task2_start.")
        elif task_id_finished == 2 and self.task_stage == 2:
            self.task_stage = 1
            print(f"Car task stage is now {self.task_stage}. Ready for next cycle.")

    def stop_thread(self):
        self.stopped = True
        if self.reader_thread.is_alive():
            self.reader_thread.join()

    def get_received_log(self):
        with self.reader_lock:
            return list(self.received_log)

    def get_sent_log(self):
        return list(self.sent_log)

    def send_command(self, command_string):
        with self.send_lock:
            if not self.serial_port:
                return
            packet_to_send = f"##{command_string}\r\n"
            log_message = f"[{time.strftime('%H:%M:%S')}] {command_string}"
            self.sent_log.append(log_message)
            self.serial_port.write_str(packet_to_send)
