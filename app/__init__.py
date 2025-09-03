# my_flask_app/app/__init__.py

from flask import Flask
from config import Config

# 1. 导入我们的控制器类和视觉处理器类
from .modules.arm_control import ArmController
from .modules.vision import VisionProcessor
from .modules.car_control import CarController


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 2. 在这里实例化我们的核心服务
    app.arm_controller = ArmController()
    app.vision_processor = VisionProcessor()
    app.car_controller = CarController()

    # 3. 启动后台线程
    app.vision_processor.start()

    # 4. 注册蓝图
    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    return app
