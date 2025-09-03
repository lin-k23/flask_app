from app import create_app

app = create_app()

if __name__ == "__main__":
    # 使用Flask开发服务器运行
    # threaded=True 确保可以同时处理视频流请求和其它可能的请求
    # host='0.0.0.0' 使其在您的局域网上可见
    app.run(host="0.0.0.0", port=8000, threaded=True, debug=False)
