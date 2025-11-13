import asyncio
import aiohttp
import time
import os
import re
from telethon import TelegramClient

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

    async def send_to_webhook(self, lead_data):
        """Отправляет лид в Flask webhook"""
        try:
            webhook_url = f"http://localhost:5432/webhook-test/Parser"
            print(f"📤 Отправляю лид в webhook...")
            
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

    async def send_telegram_reply(self, user_id, message):
        """Отправляет сообщение пользователю в Telegram"""
        try:
            user = await self.client.get_entity(user_id)
            await self.client.send_message(user, message, link_preview=False)
            print(f"✅ Ответ отправлен пользователю {user_id}")
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")
            return False

    async def send_lead_notification(self, lead_data):
        """Отправляет уведомление о найденном лиде тебе с ПОЛНОЙ информацией"""
        try:
            message = f"🎯 НАЙДЕН ЛИД #{self.leads_found + 1}!\n\n"
            message += f"📝 **Сообщение:** {lead_data['text']}\n\n"
            message += f"👤 **Пользователь:** {lead_data['user_name']}\n"
            message += f"🔗 **Username:** {lead_data.get('username', 'нет')}\n"
            message += f"🆔 **User ID:** {lead_data['user_id']}\n"
            message += f"📊 **Группа:** {lead_data['group_name']}\n"
            message += f"🔗 **Ссылка:** {lead_data['message_url']}\n"
            message += f"🕒 **Время:** {lead_data['message_time']}\n"
            message += f"🔑 **Ключевые слова:** {', '.join(lead_data['keywords'])}"
            
            await self.send_telegram_reply(YOUR_USER_ID, message)
            print(f"✅ Уведомление отправлено тебе")
            return True
        except Exception as e:
            print(f"❌ Ошибка уведомления: {e}")
            return False

    def load_groups_from_txt(self):
        """Загружает группы из текстового файла"""
        groups = []
        try:
            with open('groups.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        groups.append(line)
            
            if groups:
                print(f"✅ Загружено групп из groups.txt: {len(groups)}")
                return groups
            else:
                print("📝 Используем тестовые группы")
                return ['@dubai_community', '@dubai_work', '@uae_jobs']
                
        except FileNotFoundError:
            print("📝 Файл groups.txt не найден, используем тестовые группы")
            return ['@dubai_community', '@dubai_work', '@uae_jobs']
        except Exception as e:
            print(f"❌ Ошибка загрузки groups.txt: {e}")
            return ['@dubai_community', '@dubai_work', '@uae_jobs']

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
                    "username": f"@{username}" if username else "нет",
                    "user_id": user_id,
                    "full_name": full_name if full_name else "Неизвестно"
                }
        except Exception as e:
            print(f"⚠️ Ошибка получения информации о пользователе: {e}")
        
        return {"username": "нет", "user_id": None, "full_name": "Неизвестно"}

    async def start_real_monitoring(self):
        """НАСТОЯЩИЙ мониторинг Telegram групп"""
        print("🚀 ЗАПУСК НАСТОЯЩЕГО МОНИТОРИНГА TELEGRAM...")
        
        try:
            self.client = TelegramClient('session', self.api_id, self.api_hash)
            await self.client.start()
            
            me = await self.client.get_me()
            print(f"✅ Авторизован как: {me.first_name}")
            
            # Загружаем группы из текстового файла
            groups = self.load_groups_from_txt()
            
            print(f"🔍 Мониторим {len(groups)} групп: {groups}")
            
            # Ключевые слова
            keywords = [
                "получить допуск для рабочих", "рабочий допуск на виллу", "пасс для рабочих", 
                "пасс для работ на квартире", "пасс для работ на вилле", "пропуск для рабочих",
                "пропуск для рабочих на квартиру", "пропуск для рабочих на виллу", "разрешение на работы", 
                "допуск для рабочих", "рабочий пропуск", "пропуск для ремонтников",
                "разрешение на ремонт", "допуск на объект", "пропуск на виллу",
                "оформить пропуск", "получить пропуск", "нужен допуск"
            ]
            
            print(f"✅ Ключевых слов: {len(keywords)}")
            print("🔍 Начинаем настоящий мониторинг...")
            
            self.is_running = True
            
            while self.is_running:
                print(f"🔄 Проверка групп - {time.strftime('%H:%M:%S')} - Лидов: {self.leads_found}")
                
                for group_link in groups:
                    try:
                        group = await self.safe_get_entity(group_link)
                        if not group:
                            print(f"⚠️ Не удалось получить группу: {group_link}")
                            continue
                            
                        group_name = getattr(group, 'title', str(group_link))
                        print(f"🔎 Проверяем группу: {group_name}")
                        
                        # Получаем последние сообщения
                        messages = await self.client.get_messages(group, limit=10)
                        
                        for msg in messages:
                            if msg.text:
                                message_id = f"{getattr(group, 'id', 'unknown')}_{msg.id}"
                                
                                if message_id not in self.processed_messages:
                                    text = msg.text.lower()
                                    found_keywords = [kw for kw in keywords if kw in text]
                                    
                                    if found_keywords:
                                        print(f"🎯 НАЙДЕНО В '{group_name}': {found_keywords[0]}")
                                        
                                        user_info = self.get_user_info(msg)
                                        message_time = msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else "Неизвестно"
                                        message_url = self.get_message_url(group, msg.id, group_link)
                                        
                                        lead_data = {
                                            "source": "telegram",
                                            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                                            "text": msg.text,
                                            "keywords": found_keywords,
                                            "group_name": group_name,
                                            "user_name": user_info['full_name'],
                                            "username": user_info['username'],
                                            "user_id": user_info['user_id'],
                                            "message_time": message_time,
                                            "message_url": message_url
                                        }
                                        
                                        # Отправляем лид в webhook
                                        webhook_success = await self.send_to_webhook(lead_data)
                                        
                                        if webhook_success:
                                            # Отправляем уведомление тебе с полной информацией
                                            await self.send_lead_notification(lead_data)
                                            
                                            # ⚠️ УБРАЛ ОТВЕТ ПОЛЬЗОВАТЕЛЮ - больше не отвечаем
                                            # if user_info['user_id'] and user_info['user_id'] != YOUR_USER_ID:
                                            #     await self.send_telegram_reply(
                                            #         user_info['user_id'],
                                            #         "✅ Ваша заявка на допуск принята! С вами свяжутся в ближайшее время для оформления."
                                            #     )
                                        
                                        self.processed_messages.add(message_id)
                                        await asyncio.sleep(2)
                        
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        print(f"❌ Ошибка в группе {group_link}: {e}")
                        await asyncio.sleep(5)
                
                print("⏸️ Перерыв 60 секунд...")
                for i in range(60):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"💥 Ошибка мониторинга: {e}")
            await asyncio.sleep(30)
            if self.is_running:
                await self.start_real_monitoring()

    async def start_monitoring(self):
        """Запускает мониторинг"""
        print("🚀 Запуск Telegram мониторинга...")
        
        try:
            if os.path.exists('session.session'):
                print("✅ Найден session файл, запускаем НАСТОЯЩИЙ мониторинг")
                await self.start_real_monitoring()
            else:
                print("❌ Файл session.session не найден")
                return
            
        except Exception as e:
            print(f"💥 Критическая ошибка: {e}")
            await asyncio.sleep(60)
            if self.is_running:
                await self.start_monitoring()

async def main():
    monitor = TelegramMonitor()
    await monitor.start_monitoring()

if __name__ == '__main__':
    print("🤖 Telegram Monitor starting...")
    asyncio.run(main())
