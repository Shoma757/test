import asyncio
import aiohttp
import time
import os  # ← ВАЖНО: добавить этот импорт
from telethon import TelegramClient

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
        self.total_leads_found = 0

    async def send_to_webhook(self, lead_data):
        """Отправляет лид в Flask webhook"""
        try:
            webhook_url = f"http://localhost:5432/webhook-test/Parser"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=lead_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        print(f"✅ Лид отправлен (всего: {self.total_leads_found})")
                        return True
                    else:
                        print(f"❌ Ошибка отправки: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Ошибка webhook: {e}")
            return False

    async def start_monitoring(self):
        """Запускает мониторинг Telegram"""
        print("🚀 Запуск Telegram мониторинга...")
        
        try:
            self.client = TelegramClient('session', self.api_id, self.api_hash)
            
            # Используем session файл
            await self.client.start()
            me = await self.client.get_me()
            print(f"✅ Авторизован как: {me.first_name}")
            
            self.is_running = True
            
            # Здесь будет твой код мониторинга групп
            # Пока имитируем работу
            counter = 0
            while self.is_running:
                counter += 1
                print(f"🔍 Проверка Telegram #{counter}")
                
                # Имитируем найденный лид
                lead_data = {
                    "source": "telegram",
                    "text": f"Тестовое сообщение #{counter}",
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "keywords": ["допуск для рабочих"]
                }
                
                await self.send_to_webhook(lead_data)
                await asyncio.sleep(30)  # Проверка каждые 30 секунд
                
        except Exception as e:
            print(f"💥 Ошибка Telegram: {e}")

async def main():
    monitor = TelegramMonitor()
    await monitor.start_monitoring()

if __name__ == '__main__':
    print("🤖 Telegram Monitor starting...")
    asyncio.run(main())
