from flask import Flask, request, jsonify
import asyncio
from telethon import TelegramClient
import aiohttp
import re
import time
import threading
import os
import csv

app = Flask(__name__)

# Глобальные переменные
monitor_thread = None
is_monitoring = False

# ВАШИ ДАННЫЕ TELEGRAM
API_ID = 14535587
API_HASH = '007b2bc4ed88c84167257c4a57dd3e75'
PHONE = '+77762292659'

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
        """Отправляет лид в n8n через наш же Flask"""
        try:
            # Отправляем самому себе на локальный порт
            webhook_url = f"http://localhost:{os.environ.get('PORT', 5432)}/webhook-test/Parser"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=lead_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        print(f"✅ Лид отправлен в webhook (всего: {self.total_leads_found})")
                        return True
                    else:
                        print(f"❌ Ошибка отправки: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Ошибка webhook: {e}")
            return False

    def load_groups_from_csv(self):
        """Загружает группы из CSV (вместо Excel)"""
        groups = []
        try:
            with open('groups.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        groups.append(row[0].strip())
            print(f"✅ Загружено групп из CSV: {len(groups)}")
        except:
            print("📝 Используем тестовые группы")
            groups = ['@test_group_1', '@test_group_2']
        return groups

    def clean_group_link(self, link):
        """Очищает ссылку на группу"""
        if not link:
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
        print("🚀 === ЗАПУСК ТЕЛЕГРАМ МОНИТОРИНГА ===")
        
        try:
            self.client = TelegramClient('session', self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            
            me = await self.client.get_me()
            print(f"✅ Авторизован как: {me.first_name} (@{me.username})")
            
            # Загружаем группы из CSV
            raw_groups = self.load_groups_from_csv()
            groups = []
            
            for link in raw_groups:
                cleaned = self.clean_group_link(link)
                if cleaned and cleaned not in groups:
                    groups.append(cleaned)
            
            print(f"✅ Обработано групп: {len(groups)}")
            
            # Ключевые слова
            keywords = [
                "получить допуск для рабочих", "рабочий допуск на виллу", "пасс для рабочих", 
                "пропуск для рабочих", "разрешение на работы", "допуск для рабочих"
            ]
            
            print(f"✅ Ключевых слов: {len(keywords)}")
            print("🔍 Начинаем мониторинг...")
            
            total_cycles = 0
            self.is_running = True
            
            while self.is_running:
                total_cycles += 1
                print(f"🔄 ЦИКЛ {total_cycles} - {time.strftime('%H:%M:%S')}")
                print(f"📈 Всего лидов: {self.total_leads_found}")
                
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
                                        print(f"🎯 НАЙДЕНО в '{group_name}': {found_keywords[0]}")
                                        
                                        user_info = self.get_user_info(msg)
                                        message_url = self.get_message_url(group, msg.id, group_link)
                                        message_time = msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else "Неизвестно"
                                        
                                        lead_data = {
                                            "source": "telegram_monitor",
                                            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                                            "message_text": msg.text[:500],
                                            "keywords": found_keywords,
                                            "group": group_name,
                                            "user": user_info,
                                            "message_url": message_url
                                        }
                                        
                                        success = await self.send_to_webhook(lead_data)
                                        if success:
                                            self.total_leads_found += 1
                                        
                                        self.processed_messages.add(message_id)
                                        await asyncio.sleep(1)  # Короткая пауза
                        
                        await asyncio.sleep(3)  # Пауза между группами
                        
                    except Exception as e:
                        print(f"❌ Ошибка в группе {group_link}: {e}")
                        await asyncio.sleep(5)
                
                print("⏸️ Перерыв 30 секунд...")
                for i in range(30):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"💥 Ошибка: {e}")
            await asyncio.sleep(30)
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
    """Запускает асинхронный мониторинг в фоновом режиме"""
    try:
        # Создаем отдельный event loop для фоновой задачи
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем мониторинг
        loop.run_until_complete(monitor.start_monitoring())
    except Exception as e:
        print(f"❌ Ошибка мониторинга: {e}")

# Flask роуты для n8n - ПРИОРИТЕТ 1
@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Telegram Monitor is running!",
        "monitoring": is_monitoring,
        "leads_found": monitor.total_leads_found
    })

@app.route('/webhook-test/Parser', methods=['POST'])
def webhook_parser():
    """Webhook для n8n - ГЛАВНЫЙ ЭНДПОИНТ"""
    data = request.get_json()
    print("✅ Данные из n8n:", data)
    return jsonify({
        "status": "success", 
        "message": "Data received",
        "leads_found": monitor.total_leads_found
    })

@app.route('/start-monitor', methods=['POST'])
def start_monitor():
    """Запускает мониторинг - ОПЦИОНАЛЬНО"""
    global monitor_thread, is_monitoring
    
    if is_monitoring:
        return jsonify({"status": "already_running"})
    
    # Запускаем Telegram мониторинг в фоновом потоке
    monitor_thread = threading.Thread(target=run_async_monitor)
    monitor_thread.daemon = True  # Демон-поток (умрет с основным)
    monitor_thread.start()
    is_monitoring = True
    
    return jsonify({"status": "started"})

@app.route('/stop-monitor', methods=['POST'])
def stop_monitor():
    """Останавливает мониторинг - ОПЦИОНАЛЬНО"""
    global is_monitoring
    
    # Останавливаем через asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.stop_monitoring())
    except:
        pass
    
    is_monitoring = False
    return jsonify({"status": "stopped"})

@app.route('/status')
def status():
    return jsonify({
        "monitoring": is_monitoring,
        "leads_found": monitor.total_leads_found
    })

@app.route('/health', methods=['GET'])
def health():
    """Для проверки здоровья сервера"""
    return jsonify({"status": "healthy", "flask": "running"})

if __name__ == '__main__':
    # Flask - ПРИОРИТЕТ 1: запускаем сразу
    port = int(os.environ.get('PORT', 5432))
    
    # Telegram - ПРИОРИТЕТ 2: запускаем в фоне, если нужно
    # ЗАКОММЕНТИРУЙТЕ эти строки если хотите запускать мониторинг через API
    # monitor_thread = threading.Thread(target=run_async_monitor)
    # monitor_thread.daemon = True
    # monitor_thread.start()
    # is_monitoring = True
    
    print(f"🚀 Flask Server starting on port {port} (PRIORITY 1)")
    print(f"📡 Telegram Monitor: {'AUTO-START' if is_monitoring else 'MANUAL START via /start-monitor'}")
    
    # Запускаем Flask - это блокирующая операция
    app.run(host='0.0.0.0', port=port, debug=False)
