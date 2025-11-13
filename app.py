from flask import Flask, request, jsonify
import os
import asyncio
import threading
import time
import aiohttp
import pandas as pd
from telethon import TelegramClient, events
import re

app = Flask(__name__)

# Глобальные переменные
leads_found = 0
monitor = None
is_monitoring = False

# ТВОИ ДАННЫЕ TELEGRAM
API_ID = 21725084
API_HASH = '08f630cd0e979c07b93527ea554fe7bc'
PHONE = '+79160002004'
YOUR_USER_ID = 995290094

class TelegramMonitor:
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.phone = PHONE
        self.client = None
        self.is_running = False
        self.leads_found = 0
        self.processed_messages = set()
        self.session_file = 'telegram_session'

    async def init_client(self):
        """Инициализация Telegram клиента"""
        try:
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                print("Требуется авторизация...")
                await self.client.send_code_request(self.phone)
                # В продакшене нужно сохранить код заранее или использовать bot token
                return False
            
            me = await self.client.get_me()
            print(f"Авторизован как: {me.first_name}")
            return True
            
        except Exception as e:
            print(f"Ошибка инициализации клиента: {e}")
            return False

    async def send_to_webhook(self, lead_data):
        """Отправляет лид в webhook"""
        global leads_found
        try:
            webhook_url = "https://primary-production-9c67.up.railway.app/webhook/Parser"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=lead_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        leads_found += 1
                        self.leads_found += 1
                        return True
                    else:
                        print(f"Webhook ошибка: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"Ошибка подключения к webhook: {e}")
            return False

    async def start_monitoring(self):
        """Запускает мониторинг"""
        print("Запуск мониторинга Telegram...")
        
        if not await self.init_client():
            print("Не удалось инициализировать клиент")
            return False
        
        self.is_running = True
        
        # Загружаем группы из Excel
        groups = self.load_groups_from_excel()
        keywords = [
            "получить допуск для рабочих", "рабочий допуск", "пасс для рабочих",
            "пропуск для рабочих", "разрешение на работы", "working permit"
        ]
        
        print(f"Мониторим {len(groups)} групп")
        
        while self.is_running:
            try:
                for group_link in groups:
                    if not self.is_running:
                        break
                    
                    try:
                        group = await self.client.get_entity(group_link)
                        messages = await self.client.get_messages(group, limit=10)
                        
                        for msg in messages:
                            if msg.text:
                                message_id = f"{getattr(group, 'id', 'unknown')}_{msg.id}"
                                
                                if message_id not in self.processed_messages:
                                    text = msg.text.lower()
                                    found_keywords = [kw for kw in keywords if kw in text]
                                    
                                    if found_keywords:
                                        print(f"НАЙДЕН ЛИД: {found_keywords[0]}")
                                        
                                        lead_data = {
                                            "text": msg.text,
                                            "keywords": found_keywords,
                                            "group_name": getattr(group, 'title', str(group_link)),
                                            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                                        }
                                        
                                        await self.send_to_webhook(lead_data)
                                        self.processed_messages.add(message_id)
                    
                    except Exception as e:
                        print(f"Ошибка в группе {group_link}: {e}")
                    
                    await asyncio.sleep(5)
                
                # Пауза между циклами
                for i in range(300):  # 5 минут
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"Ошибка мониторинга: {e}")
                await asyncio.sleep(30)
        
        return True

    def load_groups_from_excel(self):
        """Загружает группы из Excel"""
        try:
            df = pd.read_excel('bot1.xlsx')
            groups = []
            
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['group', 'link']):
                    raw_groups = df[col].dropna().tolist()
                    for link in raw_groups:
                        cleaned = self.clean_group_link(str(link))
                        if cleaned:
                            groups.append(cleaned)
                    break
            
            return groups if groups else ['@dubai_community', '@dubai_work']
            
        except Exception as e:
            print(f"Ошибка загрузки Excel: {e}")
            return ['@dubai_community', '@dubai_work']

    def clean_group_link(self, link):
        """Очищает ссылку на группу"""
        link = str(link).strip()
        
        if 't.me/' in link:
            username = link.split('t.me/')[-1].split('/')[0]
            return f"@{username}" if username else None
        
        if link.startswith('@'):
            return link
        
        return link

    async def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        if self.client:
            await self.client.disconnect()
        print("Мониторинг остановлен")

# Функция для запуска мониторинга в отдельном потоке
def start_monitor_thread():
    global monitor, is_monitoring
    try:
        monitor = TelegramMonitor()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.start_monitoring())
        is_monitoring = True
    except Exception as e:
        print(f"Ошибка в мониторинге: {e}")
        is_monitoring = False

def stop_monitor_thread():
    global monitor, is_monitoring
    if monitor:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.stop_monitoring())
    is_monitoring = False

# Flask endpoints
@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Flask + Telegram Monitor is running!",
        "leads_found": leads_found,
        "monitoring_status": "running" if is_monitoring else "stopped"
    })

@app.route('/webhook/Parser', methods=['POST', 'GET'])
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

@app.route('/webhook-test/Parser', methods=['POST', 'GET'])
def webhook_parser_test():
    global leads_found
    
    if request.method == 'GET':
        return jsonify({
            "status": "ready", 
            "message": "Test webhook is working",
            "total_leads": leads_found
        })
    
    data = request.get_json() or {}
    print(f"Received TEST lead: {data}")
    
    return jsonify({
        "status": "success",
        "message": "Test lead received",
        "received_data": data
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy", 
        "monitoring": is_monitoring,
        "leads_found": leads_found
    })

@app.route('/restart', methods=['POST'])
def restart_monitor():
    """Перезапускает мониторинг"""
    try:
        # Останавливаем текущий мониторинг
        stop_monitor_thread()
        
        # Запускаем новый через 3 секунды
        def delayed_start():
            time.sleep(3)
            start_monitor_thread()
        
        threading.Thread(target=delayed_start, daemon=True).start()
        
        return jsonify({
            "status": "restarting", 
            "message": "Monitor restart initiated",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/start', methods=['POST'])
def start_monitor():
    """Запускает мониторинг"""
    global is_monitoring
    
    if is_monitoring:
        return jsonify({"status": "already_running", "message": "Monitor is already running"})
    
    try:
        threading.Thread(target=start_monitor_thread, daemon=True).start()
        return jsonify({
            "status": "started", 
            "message": "Monitor started successfully",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_monitor():
    """Останавливает мониторинг"""
    global is_monitoring
    
    if not is_monitoring:
        return jsonify({"status": "already_stopped", "message": "Monitor is already stopped"})
    
    try:
        stop_monitor_thread()
        return jsonify({
            "status": "stopped", 
            "message": "Monitor stopped successfully",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Возвращает статус мониторинга"""
    return jsonify({
        "monitoring": is_monitoring,
        "leads_found": leads_found,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    })

# Запускаем мониторинг при старте сервера
@app.before_first_request
def startup():
    print("Server starting...")
    # Автозапуск мониторинга при старте
    threading.Thread(target=start_monitor_thread, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5432))
    print(f"Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
