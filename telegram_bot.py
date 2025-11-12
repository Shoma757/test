import asyncio
import aiohttp
import time
import requests
from telethon import TelegramClient

# Ваши данные
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
        self.total_leads_found = 0

    async def send_to_webhook(self, lead_data):
        """Отправляет лид в Flask webhook"""
        try:
            webhook_url = f"http://localhost:{os.environ.get('PORT', 5432)}/webhook-test/Parser"
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
        """Упрощенный мониторинг для теста"""
        print("🚀 Запуск Telegram мониторинга...")
        
        try:
            self.client = TelegramClient('session', self.api_id, self.api_hash)
            
            # Если есть session файл - используем его
            if os.path.exists('session.session'):
                await self.client.start()
                me = await self.client.get_me()
                print(f"✅ Авторизован как: {me.first_name}")
            else:
                print("❌ Файл session.session не найден")
                print("📱 Запускаем авторизацию...")
                await self.client.start(phone=self.phone)
            
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
