from flask import Flask, request, jsonify
import os
import threading
import time
import asyncio
import aiohttp
from telethon import TelegramClient

app = Flask(__name__)

# Ваши данные
API_ID = 14535587
API_HASH = '007b2bc4ed88c84167257c4a57dd3e75'
PHONE = '+77762292659'

leads_found = 0
is_monitoring = False

class TelegramMonitor:
    def __init__(self):
        self.client = None
        self.is_running = False

    async def send_to_webhook(self, lead_data):
        """Отправляет лид в webhook"""
        try:
            railway_url = os.environ.get('RAILWAY_STATIC_URL', 'http://localhost:5432')
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{railway_url}/webhook-test/Parser",
                    json=lead_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        print("✅ Лид отправлен в webhook")
                        return True
                    else:
                        print(f"❌ Ошибка отправки: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Ошибка webhook: {e}")
            return False

    async def start_monitoring(self):
        """Запускает Telegram мониторинг"""
        print("🚀 Запуск Telegram мониторинга...")
        
        try:
            self.client = TelegramClient('session', API_ID, API_HASH)
            
            # Если есть session файл - используем его
            if os.path.exists('session.session'):
                await self.client.start()
                me = await self.client.get_me()
                print(f"✅ Авторизован как: {me.first_name}")
            else:
                print("❌ Файл session.session не найден")
                return
            
            self.is_running = True
            
            # Имитируем мониторинг
            counter = 0
            while self.is_running:
                counter += 1
                print(f"🔍 Проверка Telegram #{counter}")
                
                # Имитируем найденный лид
                lead_data = {
                    "source": "telegram",
                    "text": f"Тестовое сообщение #{counter}",
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                await self.send_to_webhook(lead_data)
                await asyncio.sleep(30)
                
        except Exception as e:
            print(f"💥 Ошибка Telegram: {e}")

    async def stop_monitoring(self):
        self.is_running = False
        if self.client:
            await self.client.disconnect()

def run_telegram_monitor():
    """Запускает Telegram мониторинг в отдельном потоке"""
    monitor = TelegramMonitor()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    global is_monitoring
    while True:
        if is_monitoring and not monitor.is_running:
            loop.run_until_complete(monitor.start_monitoring())
        elif not is_monitoring and monitor.is_running:
            loop.run_until_complete(monitor.stop_monitoring())
        
        time.sleep(5)

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
    print(f"✅ Получен лид #{leads_found + 1}")
    
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
    return jsonify({"status": "started"})

@app.route('/stop-monitor', methods=['POST'])
def stop_monitor():
    global is_monitoring
    is_monitoring = False
    return jsonify({"status": "stopped"})

if __name__ == '__main__':
    # Запускаем Telegram мониторинг в фоне
    telegram_thread = threading.Thread(target=run_telegram_monitor)
    telegram_thread.daemon = True
    telegram_thread.start()
    
    port = int(os.environ.get('PORT', 5432))
    print(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
