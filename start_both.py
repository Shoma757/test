import subprocess
import sys
import time
import os

def start_flask():
    """Запускает Flask в отдельном процессе"""
    print("🚀 Запуск Flask сервера...")
    return subprocess.Popen([sys.executable, "app.py"])

def start_telegram():
    """Запускает Telegram мониторинг в отдельном процессе"""
    print("🤖 Запуск Telegram мониторинга...")
    return subprocess.Popen([sys.executable, "telegram_bot.py"])

if __name__ == '__main__':
    print("🎯 Запуск обоих сервисов...")
    
    # Запускаем Flask
    flask_process = start_flask()
    time.sleep(5)  # Ждем запуска Flask
    
    # Запускаем Telegram
    telegram_process = start_telegram()
    
    print("✅ Оба сервиса запущены!")
    print("📡 Flask доступен по порту:", os.environ.get('PORT', 5432))
    print("🔍 Telegram мониторинг активен")
    
    try:
        # Ждем завершения процессов
        flask_process.wait()
        telegram_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервисов...")
        flask_process.terminate()
        telegram_process.terminate()
