from flask import Flask, request, jsonify
import os
import threading
import time
import requests

app = Flask(__name__)

leads_found = 0
is_monitoring = False

def simple_telegram_monitor():
    """Простой имитатор Telegram мониторинга"""
    global leads_found
    
    while True:
        if is_monitoring:
            print("🔍 Имитация проверки Telegram...")
            
            # Имитируем найденный лид
            lead_data = {
                "source": "telegram",
                "message": "Тестовое сообщение с ключевыми словами",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "keywords": ["допуск для рабочих", "пропуск для рабочих"]
            }
            
            # Отправляем самому себе в webhook
            try:
                # Получаем URL нашего приложения
                railway_url = os.environ.get('RAILWAY_STATIC_URL', f'http://localhost:{os.environ.get("PORT", 5432)}')
                response = requests.post(
                    f"{railway_url}/webhook-test/Parser",
                    json=lead_data,
                    timeout=10
                )
                if response.status_code == 200:
                    print("✅ Тестовый лид отправлен")
            except Exception as e:
                print(f"❌ Ошибка отправки: {e}")
            
        time.sleep(60)  # Проверка каждую минуту

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
    print(f"✅ Получен лид #{leads_found + 1}: {data}")
    
    leads_found += 1
    
    return jsonify({
        "status": "success",
        "message": f"Lead #{leads_found} received",
        "received_data": data
    })

@app.route('/start-monitor', methods=['POST'])
def start_monitor():
    global is_monitoring
    is_monitoring = True
    print("🚀 Мониторинг запущен")
    return jsonify({"status": "started", "message": "Monitoring started"})

@app.route('/stop-monitor', methods=['POST'])
def stop_monitor():
    global is_monitoring
    is_monitoring = False
    print("🛑 Мониторинг остановлен")
    return jsonify({"status": "stopped", "message": "Monitoring stopped"})

@app.route('/status')
def status():
    return jsonify({
        "monitoring": is_monitoring,
        "leads_found": leads_found
    })

if __name__ == '__main__':
    # Запускаем мониторинг в фоне
    monitor_thread = threading.Thread(target=simple_telegram_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Railway использует порт из переменной окружения PORT
    port = int(os.environ.get('PORT', 5432))
    print(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
