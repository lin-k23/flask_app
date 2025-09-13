# app/routes/main.py
from flask import Blueprint, render_template, Response, jsonify, request, current_app
import time
import os
import signal
from .. import stop_background_threads, start_background_services

main_bp = Blueprint("main", __name__)


def gen_frames(app):
    with app.app_context():
        while True:
            frame = current_app.vision_processor.get_latest_frame()
            if frame:
                yield (
                    b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(0.05)


@main_bp.route("/")
def index():
    return render_template("home.html")


@main_bp.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(current_app._get_current_object()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@main_bp.route("/api/system_status", methods=["GET"])
def get_system_status():
    return jsonify(current_app.state_manager)


# --- [核心修改] Task 1 调试按钮功能保持不变 ---
@main_bp.route("/api/debug_task1_direct", methods=["POST"])
def debug_task1_direct():
    response_message = current_app.arm_controller.send_task1_command()
    return jsonify({"status": "success", "message": response_message})


# --- [核心修改] Task 2 调试按钮现在发送实时AprilTag坐标 ---
@main_bp.route("/api/debug_task2_direct", methods=["POST"])
def debug_task2_direct():
    """
    获取最新的视觉数据，如果检测到AprilTag，则直接将其坐标发送给机械臂。
    这用于独立调试视觉定位功能。
    """
    vision = current_app.vision_processor
    arm = current_app.arm_controller
    data = vision.get_latest_data()
    tag_data = data.get("apriltag")

    if tag_data and tag_data.get("detected"):
        response_message = arm.send_april_tag_offset(
            tag_data.get("offset_x", 0),
            tag_data.get("offset_y", 0),
            tag_data.get("distance", 0),
            tag_data.get("id", -1),
        )
        return jsonify(
            {"status": "success", "message": f"已发送AprilTag数据: {response_message}"}
        )
    else:
        return (
            jsonify({"status": "error", "message": "未在画面中检测到AprilTag！"}),
            404,
        )


@main_bp.route("/api/execute_task1_grab", methods=["POST"])
def execute_task1_grab():
    if current_app.state_manager["status"] != "TASK1_AWAITING_INPUT":
        return jsonify(status="error", message="系统未处于Task1等待指令状态"), 423

    response_message = current_app.arm_controller.send_task1_command()
    return jsonify({"status": "success", "message": response_message})


@main_bp.route("/api/execute_task2_place", methods=["POST"])
def execute_task2_place():
    if current_app.state_manager["status"] != "TASK2_AWAITING_INPUT":
        return jsonify(status="error", message="系统未处于Task2等待指令状态"), 423

    data = request.json
    row, col, color_id = data.get("row"), data.get("col"), data.get("color_id")
    if row is None or col is None or color_id is None:
        return jsonify(status="error", message="缺少 row, col, 或 color_id"), 400

    response_message = current_app.arm_controller.send_task2_command(row, col, color_id)
    return jsonify({"status": "success", "message": response_message})


@main_bp.route("/api/finish_current_task", methods=["POST"])
def finish_current_task():
    car = current_app.car_controller
    state_manager = current_app.state_manager
    status = state_manager["status"]

    if status in ["TASK1_AWAITING_INPUT", "TASK1_EXECUTING"]:
        print("Web command: Finishing Task 1.")
        car.send_command("task1_end")
        car.update_task_stage(1)
        state_manager["status"] = "MANUAL"
        current_app.arm_controller.stop_vision_streams()
        message = "Task 1 finished by web command."
    elif status in ["TASK2_AWAITING_INPUT", "TASK2_EXECUTING"]:
        print("Web command: Finishing Task 2.")
        car.send_command("task2_end")
        car.update_task_stage(2)
        state_manager["status"] = "MANUAL"
        current_app.arm_controller.stop_vision_streams()
        message = "Task 2 finished by web command."
    else:
        return jsonify(status="error", message="系统当前不处于可结束的任务状态"), 423

    return jsonify({"status": "success", "message": message})


@main_bp.route("/api/detection_data", methods=["GET"])
def get_detection_data():
    data = current_app.vision_processor.get_latest_data()
    return jsonify(data)


@main_bp.route("/api/send_car_command", methods=["POST"])
def send_car_command():
    if current_app.state_manager["status"] != "MANUAL":
        return jsonify(status="error", message="系统正忙于自动任务，无法手动控制"), 423
    data = request.json
    command = data.get("command")
    if not command:
        return jsonify({"status": "error", "message": "Command is empty"}), 400
    current_app.car_controller.send_command(command)
    return jsonify({"status": "success", "message": f"Command '{command}' sent to car"})


@main_bp.route("/api/set_blob_color", methods=["POST"])
def set_blob_color():
    data = request.json
    color_key = data.get("color")
    if not color_key:
        return jsonify(status="error", message="No color provided"), 400
    success, message = current_app.vision_processor.set_blob_color_key(color_key)
    if success:
        return jsonify(status="success", message=message)
    else:
        return jsonify(status="error", message=message), 400


@main_bp.route("/api/toggle_vision_feature", methods=["POST"])
def toggle_vision_feature():
    data = request.json
    feature = data.get("feature")
    enabled = data.get("enabled")

    if feature == "color_block":
        status = current_app.vision_processor.set_blob_detection_status(enabled)
        msg = f"Color block detection {'enabled' if status else 'disabled'}"
    elif feature == "qrcode":
        status = current_app.vision_processor.set_qrcode_detection_status(enabled)
        msg = f"QR code detection {'enabled' if status else 'disabled'}"
    else:
        return jsonify(status="error", message=f"Unknown feature: {feature}"), 400

    return jsonify(status="success", message=msg)


@main_bp.route("/api/arm_status", methods=["GET"])
def get_arm_status():
    log = current_app.arm_controller.get_received_log()
    return jsonify({"log": log})


@main_bp.route("/api/arm_sent_log", methods=["GET"])
def get_arm_sent_log():
    log = current_app.arm_controller.get_sent_log()
    return jsonify({"log": log})


@main_bp.route("/api/arm_vision_stream_status", methods=["GET"])
def get_arm_vision_stream_status():
    status = current_app.arm_controller.get_vision_stream_status()
    return jsonify(status)


@main_bp.route("/api/toggle_arm_vision_stream", methods=["POST"])
def toggle_arm_vision_stream():
    data = request.json
    enabled = data.get("enabled")
    if enabled:
        current_app.arm_controller.start_vision_streams()
        message = "Vision stream started by user."
    else:
        current_app.arm_controller.stop_vision_streams()
        message = "Vision stream stopped by user."
    return jsonify({"status": "success", "message": message})


@main_bp.route("/api/soft_restart", methods=["POST"])
def soft_restart():
    app = current_app._get_current_object()
    stop_background_threads(app)
    start_background_services(app)
    return jsonify({"status": "success", "message": "核心服务已重启"})


@main_bp.route("/api/shutdown", methods=["POST"])
def shutdown():
    app = current_app._get_current_object()
    stop_background_threads(app)
    time.sleep(1)
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({"status": "success", "message": "服务正在关闭..."})


@main_bp.route("/api/start_tracking", methods=["POST"])
def start_tracking():
    data = request.json
    rect = data.get("rect")
    if not rect:
        return jsonify(status="error", message="No rectangle provided"), 400
    x, y, w, h = rect.get("x"), rect.get("y"), rect.get("w"), rect.get("h")
    success = current_app.vision_processor.start_tracking(x, y, w, h)
    if success:
        return jsonify(status="success", message="Tracking started")
    else:
        return jsonify(status="error", message="Failed to start tracker"), 500


@main_bp.route("/api/stop_tracking", methods=["POST"])
def stop_tracking():
    current_app.vision_processor.stop_tracking()
    return jsonify(status="success", message="Tracking stopped")
