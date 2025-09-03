# app/__init__.py

from flask import Flask
from config import Config

from .modules.arm_control import ArmController
from .modules.vision import VisionProcessor
from .modules.car_control import CarController


def stop_background_threads(app):
    """A function to gracefully stop all running threads."""
    if hasattr(app, "vision_processor") and app.vision_processor:
        app.vision_processor.stop()
    if hasattr(app, "arm_controller") and app.arm_controller:
        app.arm_controller.stop()
    if hasattr(app, "car_controller") and app.car_controller:
        app.car_controller.stop_thread()
    print("All background threads have been stopped.")


def start_background_services(app):
    """A function to initialize and start all services."""
    print("Starting background services...")
    app.arm_controller = ArmController()
    app.vision_processor = VisionProcessor()
    app.car_controller = CarController()

    app.vision_processor.start()
    print("All background services started.")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initial start of services
    start_background_services(app)

    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    return app
