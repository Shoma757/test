import asyncio
import aiohttp
import time
import os
import re
import pandas as pd
from datetime import datetime, timedelta
from telethon import TelegramClient

# ТВОИ ДАННЫЕ TELEGRAM
API_ID = 14535587
API_HASH = '007b2bc4ed88c84167257c4a57dd3e75'
PHONE = '+77762292659'

# НАСТРОЙКИ ВРЕМЕНИ - МЕНЯЙ ЗДЕСЬ
TIME_SETTINGS = {
    'minutes_back': 15,           # Парсить сообщения за последние N минут
    'groups_per_cycle': 15,       # Количество групп за один цикл
    'delay_between_groups': 20,   # Пауза между группами (секунды)
    'break_after_cycle': 600,     # Перерыв после цикла (секунды) - 10 минут
}

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
            webhook_url = "https://primary-production-9c67.up.railway.app/webhook/Parser"
            print(f"Отправляю лид в webhook...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=lead_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        response_data = await response.json()
                        print(f"Webhook ответил: {response_data['message']}")
                        self.leads_found += 1
                        return True
                    else:
                        print(f"Webhook ошибка: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"Ошибка подключения к webhook: {e}")
            return False

    def load_groups_from_excel(self):
        """Загружает группы из Excel файла bot1.xlsx"""
        groups = []
        try:
            # Читаем Excel файл
            df = pd.read_excel('bot1.xlsx')
            print(f"Загружен Excel файл с {len(df)} строками")
            
            # Ищем колонку с группами
            group_column = None
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['group', 'link', 'url', 'username', 'id', 'telegram']):
                    group_column = col
                    break
            
            if not group_column:
                group_column = df.columns[0]
                
            print(f"Используем колонку: {group_column}")
            
            # Берем группы из найденной колонки
            raw_groups = df[group_column].dropna().tolist()
            
            for link in raw_groups:
                cleaned = self.clean_group_link(link)
                if cleaned and cleaned not in groups:
                    groups.append(cleaned)
            
            print(f"Обработано групп из Excel: {len(groups)}")
            return groups
            
        except Exception as e:
            print(f"Ошибка загрузки Excel: {e}")
            return ['@dubai_community', '@dubai_work', '@uae_jobs']

    def clean_group_link(self, link):
        """Очищает ссылку на группу из Excel"""
        if not link or pd.isna(link):
            return None
        
        link = str(link).strip()
        
        # Если это число (ID группы)
        if link.replace('-', '').isdigit():
            num_id = int(link)
            if num_id < 0 and abs(num_id) > 1000000000:
                return int(link)
            elif num_id > 0:
                return int(f"-100{num_id}")
            else:
                return int(link)
        
        # Если ссылка содержит /- или заканчивается цифрами
        if '/-' in link or re.search(r'/\d+$', link):
            link = link.split('/')[-2] if '/' in link else link
        
        # Если это t.me ссылка
        if 't.me/' in link:
            username = link.split('t.me/')[-1].split('/')[0]
            if username:
                return f"@{username}" if not username.startswith('@') else username
        
        # Если уже начинается с @
        if link.startswith('@'):
            return link
        
        return link

    async def safe_get_entity(self, identifier):
        """Безопасное получение группы"""
        try:
            return await self.client.get_entity(identifier)
        except Exception as e:
            print(f"Не удалось получить группу {identifier}: {e}")
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
            print(f"Не удалось сформировать ссылку: {e}")
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
            print(f"Ошибка получения информации о пользователе: {e}")
        
        return {"username": "нет", "user_id": None, "full_name": "Неизвестно"}

    async def start_real_monitoring(self):
        """НАСТОЯЩИЙ мониторинг Telegram групп"""
        print("ЗАПУСК НАСТОЯЩЕГО МОНИТОРИНГА TELEGRAM...")
        
        try:
            self.client = TelegramClient('session', self.api_id, self.api_hash)
            await self.client.start()
            
            me = await self.client.get_me()
            print(f"Авторизован как: {me.first_name}")
            
            # Загружаем группы ИЗ EXCEL
            all_groups = self.load_groups_from_excel()
            
            print(f"Всего групп в базе: {len(all_groups)}")
            print(f"Настройки времени: {TIME_SETTINGS}")
            
            # ОБЪЕДИНЕННЫЕ КЛЮЧЕВЫЕ СЛОВА
            keywords = [
                # Исходные ключевые слова
                "допуск", "пропуск", "пасс", "разрешение", "ремонт", "работы",
                "рабочий", "рабочие", "строитель", "строители", "строительный", "строительные",
                "permit", "work", "access", "pass", "noc", "minor", "major", 
                "управляющая", "компания", "менеджмент", "билдинг",
                "community", "management", "building", "дубай", "dubai", "оаэ", "uae",
                "квартира", "вилла", "apartment", "villa", "таунхаус", "пентхаус", "офис",
                "townhouse", "penthouse", "office", "помощь", "получение", "оформление",
                "сопровождение", "документы", "help", "permission", "approval", "construction",
                
                # Новые ключевые слова - Блок 1: Дизайнеры, архитекторы, согласования
                "интерьерный дизайнер", "interior designer", "дизайнер интерьера",
                "перепланировка квартиры", "перепланировка виллы", "replanning", "remodeling",
                "архитектор", "architect", "архитектурный проект",
                "проект нового строительства", "new construction", "строительство виллы", "villa construction",
                "строительство дома", "house construction", "строительство завода", "factory construction",
                "строительство склада", "warehouse construction",
                "расчеты и согласования", "approvals", "согласование проекта",
                "Dubai Municipality", "DM", "Dubai Development Authority", "DDA", "Trakhees",
                "Dubai Civil Defense", "DCD", "District Cooling", "EMCOOL", "EMPOWER",
                "Road And Transport Authority", "RTA", "Aviation Authority",
                "Dubai Electricity and Water Authority", "DEWA",
                "государственные инстанции", "government approvals",
                
                # Блок 1: Ремонт и строительство
                "как сделать ремонт", "how to renovate", "запустить рабочих",
                "рабочие в квартиру", "рабочие на виллу", "workers access",
                "построить здание", "build a building", "строительство на участке",
                "участок земли", "land plot", "процесс строительства", "construction process",
                "сложности строительства", "construction challenges",
                "технадзор", "author supervision", "engineering supervision",
                "авторский надзор", "надзор за стройкой", "construction supervision",
                
                # Блок 2: Строительные компании и специалисты
                "строительная компания", "construction company", "ремонт в Дубае",
                "косметический ремонт", "cosmetic renovation", "капитальный ремонт", "major renovation",
                "сервисное обслуживание кондиционеров", "AC maintenance", "AC service",
                "сантехник", "plumber", "сантехнические работы", "plumbing works",
                "электрик", "electrician", "электромонтажные работы", "electrical works",
                "плиточник", "tiler", "каменьщик", "mason", "укладка плитки", "tile installation",
                "мебельщик", "furniture maker", "столяр", "carpenter", "плотник", "woodworker",
                "комплектатор", "procurement", "комплектация объектов", "project procurement",
                
                # Общие и рекомендации
                "порекомендуйте", "рекомендуйте", "recommend", "looking for",
                "проверенный", "checked", "reliable", "надежный",
                "ищу", "ищут", "looking for", "need",
                "отзыв", "review", "recommendation",
                "ОАЭ", "Дубай", "Dubai", "Абу Даби", "Abu Dhabi", "UAE"
            ]
            
            print(f"Ключевых слов: {len(keywords)}")
            print("Начинаем настоящий мониторинг...")
            
            self.is_running = True
            cycle_count = 0
            
            while self.is_running:
                cycle_count += 1
                print(f"ЦИКЛ {cycle_count} - {time.strftime('%H:%M:%S')} - Лидов: {self.leads_found}")
                
                # Берем только N групп за цикл
                groups_to_process = all_groups[:TIME_SETTINGS['groups_per_cycle']]
                print(f"Обрабатываем {len(groups_to_process)} групп в этом цикле")
                
                # Обрабатываем группы с паузами
                for i, group_link in enumerate(groups_to_process):
                    try:
                        group = await self.safe_get_entity(group_link)
                        if not group:
                            print(f"Не удалось получить группу: {group_link}")
                            continue
                            
                        group_name = getattr(group, 'title', str(group_link))
                        print(f"Проверяем группу ({i+1}/{len(groups_to_process)}): {group_name}")
                        
                        # Рассчитываем время для фильтрации сообщений
                        time_threshold = datetime.now() - timedelta(minutes=TIME_SETTINGS['minutes_back'])
                        
                        # Получаем сообщения за последние N минут
                        messages = []
                        async for message in self.client.iter_messages(
                            group, 
                            offset_date=time_threshold,
                            reverse=True  # Сначала старые сообщения
                        ):
                            messages.append(message)
                        
                        print(f"Найдено сообщений за последние {TIME_SETTINGS['minutes_back']} минут: {len(messages)}")
                        
                        for msg in messages:
                            if msg.text:
                                # Уникальный ID сообщения (группа + ID сообщения)
                                message_id = f"{getattr(group, 'id', 'unknown')}_{msg.id}"
                                
                                if message_id not in self.processed_messages:
                                    text = msg.text.lower()
                                    found_keywords = [kw for kw in keywords if kw in text]
                                    
                                    if found_keywords:
                                        print(f"НАЙДЕНО В '{group_name}': {found_keywords[0]}")
                                        
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
                                            print(f"Лид #{self.leads_found} успешно отправлен")
                                        
                                        # Добавляем в обработанные
                                        self.processed_messages.add(message_id)
                                        await asyncio.sleep(1)
                        
                        # Пауза между группами
                        if i < len(groups_to_process) - 1:
                            print(f"Пауза {TIME_SETTINGS['delay_between_groups']} секунд...")
                            await asyncio.sleep(TIME_SETTINGS['delay_between_groups'])
                        
                    except Exception as e:
                        print(f"Ошибка в группе {group_link}: {e}")
                        await asyncio.sleep(5)
                
                # Большой перерыв после цикла
                print(f"Большой перерыв {TIME_SETTINGS['break_after_cycle']} секунд до следующего цикла...")
                for i in range(TIME_SETTINGS['break_after_cycle']):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"Ошибка мониторинга: {e}")
            await asyncio.sleep(30)
            if self.is_running:
                await self.start_real_monitoring()

    async def start_monitoring(self):
        """Запускает мониторинг"""
        print("Запуск Telegram мониторинга...")
        
        try:
            if os.path.exists('session.session'):
                print("Найден session файл, запускаем НАСТОЯЩИЙ мониторинг")
                await self.start_real_monitoring()
            else:
                print("Файл session.session не найден")
                return
            
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            await asyncio.sleep(60)
            if self.is_running:
                await self.start_monitoring()

async def main():
    monitor = TelegramMonitor()
    await monitor.start_monitoring()

if __name__ == '__main__':
    print("Telegram Monitor starting...")
    asyncio.run(main())
