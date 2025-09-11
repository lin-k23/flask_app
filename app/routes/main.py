# app/routes/main.py
from flask import Blueprint, render_template, Response, jsonify, request, current_app
import time
import os
import signal
from .. import stop_background_threads, start_background_services

main_bp = Blueprint("main", __name__)


# ... (gen_frames, index, video_feed 无变化) ...
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


@main_bp.route("/api/simulate_task1_start", methods=["POST"])
def simulate_task1_start():
    if current_app.state_manager["status"] != "MANUAL":
        return jsonify(status="error", message="无法开始模拟，系统正忙于自动任务"), 423
    message = current_app.car_controller.simulate_task1_start()
    return jsonify(status="success", message=message)


@main_bp.route("/api/simulate_task2_start", methods=["POST"])
def simulate_task2_start():
    if current_app.state_manager["status"] != "MANUAL":
        return jsonify(status="error", message="无法开始模拟，系统正忙于自动任务"), 423
    message = current_app.car_controller.simulate_task2_start()
    return jsonify(status="success", message=message)


@main_bp.route("/api/detection_data", methods=["GET"])
def get_detection_data():
    data = current_app.vision_processor.get_latest_data()
    return jsonify(data)


# --- [核心修改] 此API现在是执行Task2的唯一入口 ---
@main_bp.route("/api/execute_task2", methods=["POST"])
def execute_task2():
    # 必须在等待输入的状态下才能执行
    if current_app.state_manager["status"] != "AWAITING_TASK2_INPUT":
        return jsonify(status="error", message="系统未处于等待Task2指令的状态"), 423

    data = request.json
    row, col, color_id = data.get("row"), data.get("col"), data.get("color_id")
    if row is None or col is None or color_id is None:
        return jsonify(status="error", message="缺少 row, col, 或 color_id"), 400

    # 发送指令
    response_message = current_app.arm_controller.send_task2_command(row, col, color_id)
    return jsonify({"status": "success", "message": response_message})


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


# ... (其他路由无变化) ...
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


@main_bp.route("/api/send_vision_data", methods=["POST"])
def send_vision_data():
    req_data = request.json
    vision_data_type = req_data.get("type")
    latest_vision_data = current_app.vision_processor.get_latest_data()
    response_message = ""
    status = "error"

    if vision_data_type == "color_block":
        blob_data = latest_vision_data.get("color_block")
        if blob_data and blob_data.get("detected"):
            response_message = (
                current_app.arm_controller.send_arm_offset_and_angle_bulk(
                    blob_data.get("offset_x", 0),
                    blob_data.get("offset_y", 0),
                    blob_data.get("angle", 0),
                    blob_data.get("color_index", 0),
                )
            )
            status = "success"
        else:
            response_message = "未检测到色块，不发送"
            status = "info"

    elif vision_data_type == "apriltag":
        tag_data = latest_vision_data.get("apriltag")
        if tag_data and tag_data.get("detected"):
            response_message = current_app.arm_controller.send_april_tag_offset(
                tag_data.get("offset_x", 0),
                tag_data.get("offset_y", 0),
                tag_data.get("distance", 0),
                tag_data.get("id", -1),  # 传入ID，如果不存在则默认为-1
            )
            status = "success"
        else:
            response_message = "未检测到AprilTag，不发送"
            status = "info"
    else:
        response_message = "无效的数据类型"
    return jsonify({"status": status, "message": response_message})


@main_bp.route("/api/car_status", methods=["GET"])
def get_car_status():
    log = current_app.car_controller.get_received_log()
    return jsonify({"log": log})


@main_bp.route("/api/car_sent_log", methods=["GET"])
def get_car_sent_log():
    log = current_app.car_controller.get_sent_log()
    return jsonify({"log": log})


@main_bp.route("/api/toggle_vision_feature", methods=["POST"])
def toggle_vision_feature():
    data = request.json
    feature = data.get("feature")
    enabled = data.get("enabled")
    if feature == "color_block":
        status = current_app.vision_processor.set_blob_detection_status(enabled)
        return jsonify(
            {"status": "success", "message": f"Color block detection set to {status}"}
        )
    elif feature == "qrcode":
        status = current_app.vision_processor.set_qrcode_detection_status(enabled)
        return jsonify(
            {"status": "success", "message": f"QRCode detection set to {status}"}
        )
    return jsonify({"status": "error", "message": "Unknown feature"}), 400


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
