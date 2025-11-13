from flask import Flask, request, jsonify
import os
import threading
import time
import datetime
import schedule

app = Flask(__name__)

leads_found = 0
start_time = time.time()

def restart_application():
    """Перезапускает приложение"""
    print(f" Запланированный перезапуск в {datetime.datetime.now()}")
    os._exit(0)

def schedule_restarts():
    """Настраивает расписание перезапусков"""
    # Перезапуск каждый день в 00:00 по МСК (21:00 UTC предыдущего дня)
    schedule.every().day.at("11:37").do(restart_application)  # 21:00 UTC = 00:00 МСК
    
    print(" Планировщик запущен. Перезапуск каждый день в 00:00 МСК (21:00 UTC)")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту

@app.route('/')
def home():
    uptime = time.time() - start_time
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    
    # Следующий перезапуск
    next_restart = datetime.datetime.utcnow().replace(hour=21, minute=0, second=0)
    if datetime.datetime.utcnow() > next_restart:
        next_restart += datetime.timedelta(days=1)
    
    return jsonify({
        "status": "OK", 
        "message": "Flask Server is running!",
        "leads_found": leads_found,
        "uptime": f"{hours}h {minutes}m",
        "next_restart_UTC": "21:00 (00:00 МСК)",
        "time_until_restart": str(next_restart - datetime.datetime.utcnow()).split('.')[0]
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

@app.route('/health', methods=['GET'])
def health():
    uptime = time.time() - start_time
    return jsonify({
        "status": "healthy",
        "uptime_seconds": int(uptime),
        "leads_found": leads_found
    })

@app.route('/restart-now', methods=['POST'])
def restart_now():
    """Немедленный перезапуск по запросу"""
    print(" Немедленный перезапуск по запросу...")
    threading.Timer(2.0, restart_application).start()
    return jsonify({
        "status": "restarting",
        "message": "Application will restart in 2 seconds"
    })

# Запускаем планировщик в отдельном потоке
def start_scheduler():
    time.sleep(10)  # Ждем запуска Flask
    print(" Планировщик перезапусков запущен")
    print(" Перезапуск каждый день в 00:00 МСК (21:00 UTC)")
    schedule_restarts()

if __name__ == '__main__':
    # Запускаем планировщик в фоновом потоке
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    
    port = int(os.environ.get('PORT', 5432))
    print(f" Server starting on port {port}")
    print(" Автоперезапуск каждый день в 00:00 МСК (21:00 UTC)")
    app.run(host='0.0.0.0', port=port, debug=False)



