import subprocess
import sys
import time
import os

def start_flask():
    """Запускает Flask"""
    print("🚀 Запуск Flask сервера...")
    return subprocess.Popen([sys.executable, "app.py"])

def start_telegram():
    """Запускает Telegram мониторинг"""
    print("🤖 Запуск Telegram мониторинга...")
    return subprocess.Popen([sys.executable, "telegram_bot.py"])

if __name__ == '__main__':
    print("🎯 Запуск обоих сервисов...")
    
    # Сначала Flask
    flask_process = start_flask()
    time.sleep(5)  # Ждем запуска Flask
    
    # Потом Telegram
    telegram_process = start_telegram()
    
    print("✅ Оба сервиса запущены!")
    print("📡 Flask + Telegram работают вместе!")
    print("🔍 Telegram отправляет тестовые лиды каждые 30 секунд")
    
    try:
        # Ждем завершения
        flask_process.wait()
        telegram_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка...")
        flask_process.terminate()
        telegram_process.terminate()
