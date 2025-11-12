from flask import Flask, request, jsonify
import os
import threading
import time
import requests

app = Flask(__name__)

leads_found = 0
is_monitoring = False

def simple_monitor():
    """Простой мониторинг в фоне"""
    global leads_found
    counter = 0
    
    while True:
        if is_monitoring:
            counter += 1
            print(f"🔍 Мониторинг активен - цикл {counter}")
            
            # Имитируем найденный лид
            lead_data = {
                "source": "simple_monitor", 
                "cycle": counter,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Отправляем самому себе
            try:
                requests.post(
                    "http://localhost:8080/webhook-test/Parser",
                    json=lead_data,
                    timeout=5
                )
            except:
                pass
            
        time.sleep(30)

@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Server is running!",
        "monitoring": is_monitoring,
        "leads_found": leads_found
    })

@app.route('/webhook-test/Parser', methods=['POST'])
def webhook_parser():
    global leads_found
    data = request.get_json()
    print("✅ Данные получены:", data)
    
    leads_found += 1
    
    return jsonify({
        "status": "success", 
        "leads_found": leads_found,
        "data": data
    })

@app.route('/start-monitor', methods=['POST'])
def start_monitor():
    global is_monitoring
    is_monitoring = True
    return jsonify({"status": "started"})

if __name__ == '__main__':
    # Запускаем простой мониторинг в фоне
    monitor_thread = threading.Thread(target=simple_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
