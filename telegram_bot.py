import asyncio
import aiohttp
import time
import os

# ТВОИ ДАННЫЕ TELEGRAM
API_ID = 21725084
API_HASH = '08f630cd0e979c07b93527ea554fe7bc'
PHONE = '+79160002004'
# ТВОЙ ID ДЛЯ ОТПРАВКИ СООБЩЕНИЙ
YOUR_USER_ID = 995290094

class TelegramMonitor:
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.phone = PHONE
        self.client = None
        self.is_running = False
        self.leads_found = 0

    async def send_to_webhook(self, lead_data):
        """Отправляет лид в Flask webhook"""
        try:
            webhook_url = f"http://localhost:5432/webhook-test/Parser"
            print(f"📤 Отправляю лид #{self.leads_found + 1} в webhook...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=lead_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        response_data = await response.json()
                        print(f"✅ Webhook ответил: {response_data['message']}")
                        self.leads_found += 1
                        return True
                    else:
                        print(f"❌ Webhook ошибка: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Ошибка подключения к webhook: {e}")
            return False

    async def simple_monitor(self):
        """Упрощенный мониторинг"""
        print("🔍 Запуск Telegram мониторинга...")
        
        counter = 0
        self.is_running = True
        
        while self.is_running:
            counter += 1
            print(f"🔍 Имитация проверки Telegram #{counter}")
            
            # Имитируем найденный лид
            lead_data = {
                "source": "telegram",
                "text": f"Тестовый лид #{counter} - найдены ключевые слова: допуск для рабочих",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "keywords": ["допуск для рабочих", "пропуск для рабочих"],
                "user_name": "Тестовый пользователь",
                "group_name": "Тестовая группа",
                "user_id": YOUR_USER_ID
            }
            
            # Отправляем лид в webhook
            await self.send_to_webhook(lead_data)
            
            await asyncio.sleep(30)  # Каждые 30 секунд

    async def start_monitoring(self):
        """Запускает мониторинг"""
        try:
            await self.simple_monitor()
        except Exception as e:
            print(f"💥 Ошибка: {e}")
            await asyncio.sleep(30)
            if self.is_running:
                await self.start_monitoring()

async def main():
    monitor = TelegramMonitor()
    await monitor.start_monitoring()

if __name__ == '__main__':
    print("🤖 Telegram Monitor starting...")
    asyncio.run(main())
