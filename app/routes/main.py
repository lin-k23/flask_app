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


@main_bp.route("/api/detection_data", methods=["GET"])
def get_detection_data():
    data = current_app.vision_processor.get_latest_data()
    return jsonify(data)


@main_bp.route("/api/arm_status", methods=["GET"])
def get_arm_status():
    log = current_app.arm_controller.get_received_log()
    return jsonify({"log": log})


@main_bp.route("/api/send_arm_command", methods=["POST"])
def send_arm_command():
    command_data = request.json
    command = command_data.get("command")

    # 调用控制器方法并获取返回的详细信息
    response_message = current_app.arm_controller.handle_command(command)

    return jsonify({"status": "info", "message": response_message})


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
            # 调用控制器方法并获取返回的详细信息
            response_message = (
                current_app.arm_controller.send_arm_offset_and_angle_bulk(
                    blob_data["x"], blob_data["y"], blob_data.get("angle", 0)
                )
            )
            status = "success"
        else:
            response_message = "未检测到色块，不发送"
            status = "info"

    elif vision_data_type == "apriltag":
        tag_data = latest_vision_data.get("apriltag")
        if tag_data and tag_data.get("detected"):
            # 调用控制器方法并获取返回的详细信息
            response_message = current_app.arm_controller.send_april_tag_offset(
                tag_data["x"], tag_data["y"], 0
            )
            status = "success"
        else:
            response_message = "未检测到AprilTag，不发送"
            status = "info"

    else:
        response_message = "无效的数据类型"

    return jsonify({"status": status, "message": response_message})


# ... (小车和系统控制的路由保持不变) ...
@main_bp.route("/api/send_car_command", methods=["POST"])
def send_car_command():
    data = request.json
    command = data.get("command")
    if not command:
        return jsonify({"status": "error", "message": "Command is empty"}), 400
    current_app.car_controller.send_command(command)
    return jsonify({"status": "success", "message": f"Command '{command}' sent to car"})


@main_bp.route("/api/car_status", methods=["GET"])
def get_car_status():
    log = current_app.car_controller.get_received_log()
    return jsonify({"log": log})


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
