import threading
import time
import webview
from main import app


def run_server():
    app.run(host='127.0.0.1', port=5050, debug=False, use_reloader=False)


if __name__ == '__main__':
    server = threading.Thread(target=run_server, daemon=True)
    server.start()
    time.sleep(1.5)
    window = webview.create_window(
        'ترند سنتر الأردن - TREND CENTER JORDAN',
        'http://127.0.0.1:5050',
        width=1400,
        height=900,
        min_size=(1000, 650),
        resizable=True,
    )
    webview.start()
