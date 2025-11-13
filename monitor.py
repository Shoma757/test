import asyncio
import aiohttp
import time
import pandas as pd
from telethon import TelegramClient

# ТВОИ ДАННЫЕ TELEGRAM
API_ID = 21725084
API_HASH = '08f630cd0e979c07b93527ea554fe7bc'
PHONE = '+79160002004'

class TelegramMonitor:
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.phone = PHONE
        self.client = None
        self.is_running = False
        self.processed_messages = set()

    async def init_client(self):
        try:
            self.client = TelegramClient('telegram_session', self.api_id, self.api_hash)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                print("Требуется авторизация...")
                await self.client.send_code_request(self.phone)
                return False
            
            me = await self.client.get_me()
            print(f"Авторизован как: {me.first_name}")
            return True
        except Exception as e:
            print(f"Ошибка инициализации: {e}")
            return False

    async def send_to_webhook(self, lead_data):
        try:
            webhook_url = "https://test-production-46c0.up.railway.app/webhook-test/Parser"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=lead_data) as response:
                    if response.status == 200:
                        print(f"✅ Лид отправлен: {lead_data['keywords'][0]}")
                        return True
                    else:
                        print(f"❌ Webhook ошибка: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False

    async def start_monitoring(self):
        print("🚀 ЗАПУСК МОНИТОРИНГА TELEGRAM...")
        
        if not await self.init_client():
            print("❌ Не удалось инициализировать клиент")
            return

        self.is_running = True
        
        # Группы и ключевые слова
        groups = ['@dubai_community', '@dubai_work', '@uae_jobs']
        keywords = [
            "пропуск для рабочих", "допуск для рабочих", "рабочий допуск",
            "пасс для рабочих", "разрешение на работы", "working permit"
        ]
        
        print(f"🔍 Мониторим {len(groups)} групп")
        
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
                                        print(f"🎯 НАЙДЕНО: {found_keywords[0]}")
                                        
                                        lead_data = {
                                            "text": msg.text,
                                            "keywords": found_keywords,
                                            "group_name": getattr(group, 'title', str(group_link)),
                                            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                                            "source": "telegram_monitor"
                                        }
                                        
                                        await self.send_to_webhook(lead_data)
                                        self.processed_messages.add(message_id)
                                        await asyncio.sleep(1)
                    
                    except Exception as e:
                        print(f"⚠️ Ошибка в группе {group_link}: {e}")
                    
                    await asyncio.sleep(3)
                
                # Пауза между циклами
                print("⏸️ Перерыв 2 минуты...")
                for i in range(120):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"❌ Ошибка мониторинга: {e}")
                await asyncio.sleep(30)

async def main():
    monitor = TelegramMonitor()
    await monitor.start_monitoring()

if __name__ == '__main__':
    print("Starting Telegram Monitor...")
    asyncio.run(main())
