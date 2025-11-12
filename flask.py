from flask import Flask, jsonify
import os
import subprocess
import threading
import time

app = Flask(__name__)

# Глобальная переменная для хранения процесса
monitor_process = None

def start_monitor_process():
    """Запускает мониторинг как отдельный процесс"""
    global monitor_process
    try:
        monitor_process = subprocess.Popen(['python', 'telegram_monitor.py'])
        print("🚀 Telegram мониторинг запущен как отдельный процесс")
        return True
    except Exception as e:
        print(f"❌ Ошибка запуска мониторинга: {e}")
        return False

def stop_monitor_process():
    """Останавливает процесс мониторинга"""
    global monitor_process
    if monitor_process:
        monitor_process.terminate()
        monitor_process.wait()
        print("🛑 Telegram мониторинг остановлен")
        return True
    return False

@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Telegram Monitor Server is running!",
        "monitoring": monitor_process is not None and monitor_process.poll() is None
    })

@app.route('/start-monitor', methods=['POST'])
def start_monitor():
    """Запускает мониторинг"""
    if monitor_process and monitor_process.poll() is None:
        return jsonify({"status": "already_running", "message": "Мониторинг уже запущен"})
    
    success = start_monitor_process()
    if success:
        return jsonify({"status": "started", "message": "Мониторинг запущен"})
    else:
        return jsonify({"status": "error", "message": "Ошибка запуска"})

@app.route('/stop-monitor', methods=['POST'])
def stop_monitor():
    """Останавливает мониторинг"""
    success = stop_monitor_process()
    if success:
        return jsonify({"status": "stopped", "message": "Мониторинг остановлен"})
    else:
        return jsonify({"status": "error", "message": "Мониторинг не был запущен"})

@app.route('/status')
def status():
    is_running = monitor_process is not None and monitor_process.poll() is None
    return jsonify({
        "monitoring": is_running,
        "pid": monitor_process.pid if is_running else None
    })

@app.route('/webhook-test/Parser', methods=['GET', 'POST'])
def webhook_parser():
    """Webhook для получения данных от мониторинга"""
    if request.method == 'GET':
        return jsonify({"status": "ready"})
    
    data = request.get_json(silent=True) or {}
    print(f"✅ Получен лид: {data.get('analysis_data', {}).get('found_keywords', [])}")
    
    return jsonify({"status": "success", "received": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Server starting on port {port}")
    
    # Автоматически запускаем мониторинг при старте
    # start_monitor_process()
    
    app.run(host='0.0.0.0', port=port, debug=False)
