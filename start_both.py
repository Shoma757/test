import subprocess
import sys
import time
import os

def start_flask():
    """Запускает ТОЛЬКО Flask"""
    print("🚀 Запуск Flask сервера...")
    return subprocess.Popen([sys.executable, "app.py"])

if __name__ == '__main__':
    print("🎯 Запуск Flask сервера (Telegram отключен)...")
    
    # Запускаем ТОЛЬКО Flask
    flask_process = start_flask()
    
    print("✅ Flask сервер запущен!")
    print("📡 Webhook доступен по URL: https://test-production-46c0.up.railway.app/webhook-test/Parser")
    
    try:
        flask_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка...")
        flask_process.terminate()
