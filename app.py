from flask import Flask, request, jsonify
import asyncio
import pandas as pd
from telethon import TelegramClient
import aiohttp
import json
import re
import os
import time
import threading

app = Flask(__name__)

# Глобальные переменные
monitor_thread = None
is_monitoring = False
telegram_client = None

# ВАШИ ДАННЫЕ TELEGRAM
API_ID = 14535587
API_HASH = '007b2bc4ed88c84167257c4a57dd3e75'
PHONE = '+77762292659'
WEBHOOK_URL = "https://test-production-fb35.up.railway.app/webhook-test/Parser"

class TelegramMonitor:
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.phone = PHONE
        self.client = None
        self.is_running = False
        self.processed_messages = set()
        self.total_leads_found = 0

    async def send_to_webhook(self, lead_data):
        """Отправляет лид в webhook"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    WEBHOOK_URL,
                    json=lead_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        print(f"✅ Лид отправлен в webhook")
                        return True
                    else:
                        print(f"❌ Ошибка отправки: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Ошибка webhook: {e}")
            return False

    def clean_group_link(self, link):
        """Очищает ссылку на группу"""
        if not link or pd.isna(link):
            return None
        
        link = str(link).strip()
        
        if link.replace('-', '').isdigit():
            num_id = int(link)
            if num_id < 0 and abs(num_id) > 1000000000:
                return int(link)
            elif num_id > 0:
                return int(f"-100{num_id}")
            else:
                return int(link)
        
        if '/-' in link or re.search(r'/\d+$', link):
            link = link.split('/')[-2] if '/' in link else link
        
        if 't.me/' in link:
            username = link.split('t.me/')[-1].split('/')[0]
            if username:
                return f"@{username}" if not username.startswith('@') else username
        
        if link.startswith('@'):
            return link
        
        return link

    async def safe_get_entity(self, identifier):
        """Безопасное получение группы"""
        try:
            return await self.client.get_entity(identifier)
        except Exception as e:
            print(f"⚠️ Не удалось получить группу {identifier}: {e}")
            return None

    def get_message_url(self, group, message_id, group_link):
        """Формирует ссылку на сообщение"""
        try:
            if isinstance(group_link, str) and group_link.startswith('@'):
                return f"https://t.me/{group_link[1:]}/{message_id}"
            else:
                group_id = getattr(group, 'id', None)
                if group_id:
                    if str(group_id).startswith('-100'):
                        channel_id = str(group_id)[4:]
                    else:
                        channel_id = str(group_id).replace('-', '')
                    return f"https://t.me/c/{channel_id}/{message_id}"
        except Exception as e:
            print(f"⚠️ Не удалось сформировать ссылку: {e}")
        return "Недоступно"

    def get_user_info(self, msg):
        """Извлекает информацию о пользователе"""
        try:
            sender = msg.sender
            if sender:
                username = getattr(sender, 'username', None)
                first_name = getattr(sender, 'first_name', '')
                last_name = getattr(sender, 'last_name', '')
                user_id = getattr(sender, 'id', None)
                
                full_name = f"{first_name} {last_name}".strip()
                
                return {
                    "username": f"@{username}" if username else None,
                    "user_id": user_id,
                    "full_name": full_name if full_name else None
                }
        except Exception as e:
            print(f"⚠️ Ошибка получения информации о пользователе: {e}")
        
        return {"username": None, "user_id": None, "full_name": None}

    async def start_monitoring(self):
        """Запускает мониторинг Telegram"""
        global is_monitoring
        
        try:
            print("=== ТЕЛЕГРАМ МОНИТОРИНГ ДОПУСКОВ ===")
            print("Подключаемся к Telegram...")
            
            self.client = TelegramClient('session', self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            
            me = await self.client.get_me()
            print(f"✅ Авторизован как: {me.first_name} (@{me.username})")
            print("🔄 Загружаем группы из Excel...")
            
            # Загружаем группы
            try:
                df = pd.read_excel('bot1.xlsx')
                group_column = None
                for col in df.columns:
                    if any(keyword in col.lower() for keyword in ['group', 'link', 'url', 'username', 'id']):
                        group_column = col
                        break
                
                if not group_column:
                    group_column = df.columns[0]
                
                raw_groups = df[group_column].dropna().tolist()
                groups = []
                
                for link in raw_groups:
                    cleaned = self.clean_group_link(link)
                    if cleaned and cleaned not in groups:
                        groups.append(cleaned)
                
                print(f"📊 Загружено групп: {len(groups)}")
                
            except Exception as e:
                print(f"❌ Ошибка загрузки Excel: {e}")
                groups = []
            
            # Ключевые слова
            keywords = [
                "получить допуск для рабочих", "рабочий допуск на виллу", "пасс для рабочих", 
                "пасс для работ на квартире", "пасс для работ на вилле", "пропуск для рабочих",
                "пропуск для рабочих на квартиру", "пропуск для рабочих на виллу", "разрешение на работы", 
                "разрешение на работы от УК", "разрешение на работы от комьюнити менеджмента", 
                "разрешение на работы от билдинга", "разрешение на работы от билдинг менеджмента",
                "допуск для рабочих", "рабочий пропуск", "пропуск для ремонтников",
                "разрешение на ремонт", "допуск на объект", "пропуск на виллу",
                "пропуск в билдинг", "допуск в билдинг", "рабочий пасс",
                "оформить пропуск", "получить пропуск", "нужен допуск"
            ]
            
            print(f"🎯 Загружено ключевых слов: {len(keywords)}")
            print("🔍 Начинаем мониторинг...")
            
            total_cycles = 0
            self.is_running = True
            
            # Основной цикл мониторинга
            while self.is_running:
                total_cycles += 1
                print(f"\n🔍 ЦИКЛ {total_cycles} - {time.strftime('%H:%M:%S')}")
                print(f"📊 Всего лидов найдено: {self.total_leads_found}")
                
                if groups:
                    for group_link in groups:
                        try:
                            group = await self.safe_get_entity(group_link)
                            if not group:
                                continue
                                
                            group_name = getattr(group, 'title', str(group_link))
                            messages = await self.client.get_messages(group, limit=3)
                            
                            for msg in messages:
                                if msg.text:
                                    message_id = f"{getattr(group, 'id', 'unknown')}_{msg.id}"
                                    
                                    if message_id not in self.processed_messages:
                                        text = msg.text.lower()
                                        found_keywords = [kw for kw in keywords if kw in text]
                                        
                                        if found_keywords:
                                            print(f"🎯 НАЙДЕНО в '{group_name}': {', '.join(found_keywords)}")
                                            
                                            user_info = self.get_user_info(msg)
                                            message_url = self.get_message_url(group, msg.id, group_link)
                                            message_time = msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else "Неизвестно"
                                            
                                            lead_data = {
                                                "source": "telegram_monitor",
                                                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                                                "cycle_number": total_cycles,
                                                "message_data": {
                                                    "text": msg.text[:1000],
                                                    "message_id": msg.id,
                                                    "message_time": message_time,
                                                    "message_url": message_url
                                                },
                                                "user_data": user_info,
                                                "group_data": {
                                                    "name": group_name,
                                                    "link": str(group_link)
                                                },
                                                "analysis_data": {
                                                    "found_keywords": found_keywords,
                                                    "needs_ai_verification": True,
                                                    "ai_verified": False
                                                }
                                            }
                                            
                                            success = await self.send_to_webhook(lead_data)
                                            if success:
                                                self.total_leads_found += 1
                                            
                                            self.processed_messages.add(message_id)
                                            await asyncio.sleep(2)
                            
                            await asyncio.sleep(10)
                            
                        except Exception as e:
                            print(f"⚠️ Ошибка в группе {group_link}: {e}")
                            await asyncio.sleep(10)
                
                # Пауза между циклами
                print("💤 Перерыв 5 минут до следующего цикла...")
                for i in range(300):  # 5 минут
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"💥 Критическая ошибка: {e}")
            print("🔄 Перезапуск через 1 минуту...")
            await asyncio.sleep(60)
            if self.is_running:
                await self.start_monitoring()

    async def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        if self.client:
            await self.client.disconnect()
        print("🛑 Мониторинг остановлен")

# Создаем экземпляр монитора
monitor = TelegramMonitor()

def run_async_monitor():
    """Запускает асинхронный мониторинг в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(monitor.start_monitoring())

# Flask роуты
@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Telegram Monitor Server is running!",
        "endpoints": {
            "webhook": "POST /webhook-test/Parser",
            "start": "POST /start-monitor", 
            "stop": "POST /stop-monitor",
            "status": "GET /status"
        }
    })

@app.route('/webhook-test/Parser', methods=['GET', 'POST'])
def webhook_parser():
    """Webhook для n8n"""
    if request.method == 'GET':
        return jsonify({
            "status": "ready", 
            "message": "Send POST request with JSON data"
        })
    
    data = request.get_json(silent=True) or {}
    print(f"📨 Получены данные в webhook: {data}")
    
    return jsonify({
        "status": "success",
        "message": "Data received via POST",
        "received_data": data
    })

@app.route('/start-monitor', methods=['POST'])
def start_monitor():
    """Запускает Telegram мониторинг"""
    global monitor_thread, is_monitoring
    
    if is_monitoring:
        return jsonify({"status": "already_running", "message": "Мониторинг уже запущен"})
    
    monitor_thread = threading.Thread(target=run_async_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    is_monitoring = True
    
    return jsonify({"status": "started", "message": "Мониторинг запущен"})

@app.route('/stop-monitor', methods=['POST'])
def stop_monitor():
    """Останавливает Telegram мониторинг"""
    global is_monitoring
    
    asyncio.run(monitor.stop_monitoring())
    is_monitoring = False
    
    return jsonify({"status": "stopped", "message": "Мониторинг остановлен"})

@app.route('/status')
def status():
    return jsonify({
        "status": "running",
        "monitoring": is_monitoring,
        "leads_found": monitor.total_leads_found if monitor else 0
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port)
