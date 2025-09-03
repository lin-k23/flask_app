from flask import Blueprint, render_template, Response
from app.camera import Camera

main_bp = Blueprint("main", __name__)
camera = Camera()


def gen_frames():
    while True:
        frame = camera.get_frame()
        if frame is None:
            continue
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@main_bp.route("/")
def index():
    return render_template("home.html")


@main_bp.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
