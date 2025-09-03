from flask import Blueprint, render_template, Response, jsonify, request, current_app
import time

main_bp = Blueprint("main", __name__)


def gen_frames(app):
    """
    [核心修改] 这个生成器现在接收 app 实例作为参数，
    以便在自己的作用域内创建应用上下文。
    """
    with app.app_context():
        while True:
            # 现在，在这个 'with' 代码块内部，current_app 是安全可用的
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
    """
    [核心修改] 我们在这里获取真实的app对象，并将其传递给生成器。
    current_app._get_current_object() 是获取底层app实例的标准方法。
    """
    return Response(
        gen_frames(current_app._get_current_object()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@main_bp.route("/api/detection_data", methods=["GET"])
def get_detection_data():
    """为面板2提供检测数据。"""
    data = current_app.vision_processor.get_latest_data()
    return jsonify(data)


@main_bp.route("/api/send_arm_command", methods=["POST"])
def send_arm_command():
    """接收并处理发送给机械臂的自定义指令。"""
    command_data = request.json
    command = command_data.get("command")
    current_app.logger.info(f"收到网页指令: {command}")

    current_app.arm_controller.handle_command(command)

    return jsonify({"status": "success", "message": f"指令 '{command}' 已发送"})


@main_bp.route("/api/arm_status", methods=["GET"])
def get_arm_status():
    """提供从机械臂接收到的最新日志。"""
    log = current_app.arm_controller.get_received_log()
    return jsonify({"log": log})


@main_bp.route("/api/send_vision_data", methods=["POST"])
def send_vision_data():
    """根据前端请求，获取最新视觉数据并发送给机械臂。"""
    req_data = request.json
    vision_data_type = req_data.get("type")

    latest_vision_data = current_app.vision_processor.get_latest_data()

    if vision_data_type == "color_block":
        blob_data = latest_vision_data.get("color_block")
        if blob_data and blob_data.get("detected"):
            current_app.arm_controller.send_arm_offset_and_angle_bulk(
                blob_data["x"], blob_data["y"], 0
            )
            return jsonify({"status": "success", "message": "色块数据已发送"})
        else:
            return jsonify({"status": "error", "message": "未检测到色块"})

    elif vision_data_type == "apriltag":
        tag_data = latest_vision_data.get("apriltag")
        if tag_data and tag_data.get("detected"):
            current_app.arm_controller.send_april_tag_offset(
                tag_data["x"], tag_data["y"], 0
            )  # 暂时发送默认距离0
            return jsonify({"status": "success", "message": "AprilTag数据已发送"})
        else:
            return jsonify({"status": "error", "message": "未检测到AprilTag"})

    return jsonify({"status": "error", "message": "无效的数据类型"})
