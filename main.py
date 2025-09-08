# use
# waitress-serve --host=0.0.0.0 --port=8000 main:app
# to start to avoid warning

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True, debug=False)
