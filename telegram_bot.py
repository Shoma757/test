import asyncio
import aiohttp
import time
import os
from telethon import TelegramClient

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
                        print(f"✅ Лид отправлен в n8n")
                        return True
                    return False
        except Exception as e:
            print(f"❌ Ошибка webhook: {e}")
            return False

    async def simple_monitor(self):
        """Упрощенный мониторинг пока не починим Telethon"""
        print("🔍 Запуск упрощенного мониторинга...")
        
        counter = 0
        self.is_running = True
        
        while self.is_running:
            counter += 1
            print(f"🔍 Имитация проверки Telegram #{counter}")
            
            # Имитируем найденный лид
            lead_data = {
                "source": "telegram",
                "text": f"Тестовый лид #{counter} - найдены ключевые слова",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "keywords": ["допуск для рабочих", "пропуск для рабочих"]
            }
            
            await self.send_to_webhook(lead_data)
            await asyncio.sleep(30)  # Каждые 30 секунд

    async def start_monitoring(self):
        """Запускает мониторинг"""
        print("🚀 Запуск Telegram мониторинга...")
        
        try:
            # Пока используем упрощенную версию
            await self.simple_monitor()
            
        except Exception as e:
            print(f"💥 Критическая ошибка: {e}")
            # Автоперезапуск через 60 секунд
            await asyncio.sleep(60)
            if self.is_running:
                await self.start_monitoring()

async def main():
    monitor = TelegramMonitor()
    await monitor.start_monitoring()

if __name__ == '__main__':
    print("🤖 Telegram Monitor starting...")
    asyncio.run(main())
