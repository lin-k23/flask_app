from flask import Blueprint, render_template, Response, jsonify, request, current_app

# [重要] 导入路径指向我们设计的后台处理模块
from app.modules.vision import VisionProcessor
import time

# 全局实例化并启动视觉处理器
vision_processor = VisionProcessor()
vision_processor.start()

main_bp = Blueprint("main", __name__)


def gen_frames():
    """视频流生成器函数 从VisionProcessor获取已处理的帧。"""
    while True:
        frame = vision_processor.get_latest_frame()
        if frame:
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        # 稍微等待，匹配处理线程的帧率
        time.sleep(0.05)


@main_bp.route("/")
def index():
    """主页 渲染控制面板"""
    return render_template("home.html")


@main_bp.route("/video_feed")
def video_feed():
    """提供视频流"""
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@main_bp.route("/api/detection_data", methods=["GET"])
def get_detection_data():
    """为面板2提供检测数据"""
    data = vision_processor.get_latest_data()
    return jsonify(data)


@main_bp.route("/api/send_arm_command", methods=["POST"])
def send_arm_command():
    """为面板4接收控制指令"""
    command_data = request.json
    current_app.logger.info(f"收到机械臂指令: {command_data.get('command')}")

    # 未来可以调用: from app.modules import arm_control
    # arm_control.send_command(command_data.get('command'))

    return jsonify(
        {"status": "success", "message": f"指令 '{command_data.get('command')}' 已收到"}
    )
