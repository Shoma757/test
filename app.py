from flask import Flask, request, jsonify
import os
import subprocess
import threading
import time

app = Flask(__name__)
leads_found = 0
monitor_process = None

@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Flask Server is running!",
        "leads_found": leads_found
    })

@app.route('/webhook-test/Parser', methods=['POST', 'GET'])
def webhook_parser():
    global leads_found
    
    if request.method == 'GET':
        return jsonify({
            "status": "ready", 
            "message": "Send POST request with JSON data",
            "total_leads": leads_found
        })
    
    data = request.get_json() or {}
    print(f"Received lead #{leads_found + 1}: {data}")
    
    leads_found += 1
    
    return jsonify({
        "status": "success",
        "message": f"Lead #{leads_found} received",
        "received_data": data,
        "total_leads": leads_found
    })

@app.route('/start-monitor', methods=['POST'])
def start_monitor():
    """Запускает мониторинг как отдельный процесс"""
    global monitor_process
    
    try:
        # Проверяем, не запущен ли уже мониторинг
        if monitor_process and monitor_process.poll() is None:
            return jsonify({"status": "already_running", "message": "Monitor is already running"})
        
        # Запускаем мониторинг как отдельный процесс
        monitor_process = subprocess.Popen(['python', 'monitor.py'])
        
        return jsonify({
            "status": "started", 
            "message": "Telegram monitor started successfully",
            "pid": monitor_process.pid,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop-monitor', methods=['POST'])
def stop_monitor():
    """Останавливает мониторинг"""
    global monitor_process
    
    try:
        if monitor_process:
            monitor_process.terminate()
            monitor_process.wait()
            monitor_process = None
            
        return jsonify({
            "status": "stopped", 
            "message": "Telegram monitor stopped successfully",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/restart-monitor', methods=['POST'])
def restart_monitor():
    """Перезапускает мониторинг"""
    global monitor_process
    
    try:
        # Останавливаем текущий процесс
        if monitor_process:
            monitor_process.terminate()
            monitor_process.wait()
            time.sleep(2)
        
        # Запускаем новый процесс
        monitor_process = subprocess.Popen(['python', 'monitor.py'])
        
        return jsonify({
            "status": "restarted", 
            "message": "Telegram monitor restarted successfully",
            "pid": monitor_process.pid,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/monitor-status', methods=['GET'])
def monitor_status():
    """Проверяет статус мониторинга"""
    global monitor_process
    
    is_running = monitor_process and monitor_process.poll() is None
    
    return jsonify({
        "monitoring": is_running,
        "leads_found": leads_found,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5432))
    print(f"🚀 Flask Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
