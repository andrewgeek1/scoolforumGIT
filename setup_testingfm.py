#!/usr/bin/env python3
"""
Скрипт для настройки доступа к приложению через домен testingfm.ru
Запуск: python setup_testingfm.py
"""

import subprocess
import time
import socket
import requests
import json
from datetime import datetime
import os
import sys
import platform

class TestingFMSetup:
    """Настройка домена testingfm.ru"""
    
    def __init__(self, local_port=5000):
        self.domain = "testingfm.ru"
        self.www_domain = f"www.testingfm.ru"
        self.local_port = local_port
        self.local_url = f"http://localhost:{local_port}"
        self.public_url = f"http://{self.domain}"
        self.tunnel_process = None
        self.is_windows = platform.system() == "Windows"
        
    def get_public_ip(self):
        """Получает публичный IP"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json()['ip']
        except:
            return "НЕ УДАЛОСЬ ОПРЕДЕЛИТЬ"
    
    def get_local_ip(self):
        """Получает локальный IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "НЕ УДАЛОСЬ ОПРЕДЕЛИТЬ"
    
    def check_ssh(self):
        """Проверяет наличие SSH"""
        try:
            subprocess.run(['ssh', '-V'], capture_output=True, check=True)
            return True
        except:
            return False
    
    def setup_serveo(self):
        """Настройка через Serveo"""
        print("\n🔧 Настройка Serveo туннеля для testingfm.ru...")
        
        if not self.check_ssh():
            print("❌ SSH не найден. Установите SSH или используйте другой метод.")
            return False
        
        print("\n📡 Запускаем SSH туннель...")
        print("   Это может занять несколько секунд...\n")
        
        cmd = [
            'ssh', '-o', 'StrictHostKeyChecking=no',
            '-o', 'ServerAliveInterval=60',
            '-R', f'testingfm.ru:80:localhost:{self.local_port}',
            'serveo.net'
        ]
        
        try:
            if self.is_windows:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            time.sleep(5)
            
            if self.tunnel_process.poll() is None:
                self.print_success_serveo()
                self.save_info('serveo')
                return True
            else:
                print("❌ Ошибка создания туннеля")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def print_dns_instructions(self):
        """Инструкция по DNS"""
        public_ip = self.get_public_ip()
        local_ip = self.get_local_ip()
        
        print("\n" + "=" * 70)
        print("📝 НАСТРОЙКА DNS ДЛЯ testingfm.ru".center(70))
        print("=" * 70)
        
        print(f"""
1. ВОЙДИТЕ В ПАНЕЛЬ УПРАВЛЕНИЯ ДОМЕНОМ testingfm.ru

2. СОЗДАЙТЕ A-ЗАПИСИ:
   -------------------------------------------------
   Тип: A    | Имя: @    | Значение: {public_ip}
   Тип: A    | Имя: www  | Значение: {public_ip}
   -------------------------------------------------

3. ПРОВЕРЬТЕ ЧЕРЕЗ НЕСКОЛЬКО МИНУТ:
   nslookup testingfm.ru
   nslookup www.testingfm.ru

4. НАСТРОЙТЕ БРАНДМАУЭР (важно!):
   -------------------------------------------------
   Windows (администратор):
     netsh advfirewall firewall add rule name="School App" dir=in action=allow protocol=TCP localport={self.local_port}
   
   Linux:
     sudo ufw allow {self.local_port}
   
   macOS:
     sudo pfctl -f /etc/pf.conf
   -------------------------------------------------

5. НАСТРОЙТЕ ПРОБРОС ПОРТОВ В РОУТЕРЕ:
   Внешний порт: 80
   Внутренний порт: {self.local_port}
   Внутренний IP: {local_ip}

6. ЗАПУСТИТЕ ПРИЛОЖЕНИЕ:
   python app.py --host 0.0.0.0 --port {self.local_port}

7. ГОТОВО! Ваше приложение будет доступно по адресам:
   • http://testingfm.ru
   • http://www.testingfm.ru
   • http://{local_ip}:{self.local_port} (в локальной сети)
""")
    
    def print_success_serveo(self):
        """Успешная настройка Serveo"""
        print("\n" + "=" * 70)
        print("✅ ТУННЕЛЬ ДЛЯ testingfm.ru УСПЕШНО СОЗДАН!".center(70))
        print("=" * 70)
        
        print(f"""
🌍 ВАШЕ ПРИЛОЖЕНИЕ ДОСТУПНО:

   • http://testingfm.ru
   • http://www.testingfm.ru

📍 ЛОКАЛЬНЫЙ ДОСТУП:
   • http://localhost:{self.local_port}
   • http://{self.get_local_ip()}:{self.local_port}

📝 НАСТРОЙТЕ DNS В ПАНЕЛИ УПРАВЛЕНИЯ:

   Тип: CNAME    | Имя: @    | Значение: testingfm.ru.serveo.net
   Тип: CNAME    | Имя: www  | Значение: testingfm.ru.serveo.net

⚠️  ВАЖНО:
   • Туннель работает только пока открыто это окно
   • Нажмите Ctrl+C для остановки
""")
    
    def save_info(self, method):
        """Сохраняет информацию в файл"""
        info = {
            'domain': 'testingfm.ru',
            'www_domain': 'www.testingfm.ru',
            'method': method,
            'local_port': self.local_port,
            'local_ip': self.get_local_ip(),
            'public_ip': self.get_public_ip(),
            'timestamp': datetime.now().isoformat(),
            'urls': {
                'main': 'http://testingfm.ru',
                'www': 'http://www.testingfm.ru',
                'local': f'http://localhost:{self.local_port}',
                'network': f'http://{self.get_local_ip()}:{self.local_port}'
            }
        }
        
        with open('testingfm_config.json', 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Информация сохранена в testingfm_config.json")
    
    def run(self):
        """Запуск настройки"""
        print("\n" + "=" * 70)
        print("🌐 НАСТРОЙКА ДОМЕНА testingfm.ru".center(70))
        print("=" * 70)
        
        print(f"\n📊 ИНФОРМАЦИЯ:")
        print(f"   • Домен: testingfm.ru")
        print(f"   • С www: www.testingfm.ru")
        print(f"   • Ваш IP: {self.get_public_ip()}")
        print(f"   • Локальный IP: {self.get_local_ip()}")
        print(f"   • Порт: {self.local_port}")
        
        print("\nВыберите способ настройки:")
        print("   1. 🚀 Автоматический туннель (Serveo) - быстро и просто")
        print("   2. 📝 Настройка DNS + проброс портов - для постоянного доступа")
        print("   3. ❌ Выход")
        
        choice = input("\nВаш выбор (1-3): ").strip()
        
        if choice == '1':
            if self.setup_serveo():
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n\n🛑 Останавливаем туннель...")
                    if self.tunnel_process:
                        self.tunnel_process.terminate()
            else:
                print("\n❌ Не удалось настроить туннель")
                self.print_dns_instructions()
        
        elif choice == '2':
            self.print_dns_instructions()
        
        else:
            print("\n👋 До свидания!")


def main():
    """Главная функция"""
    try:
        setup = TestingFMSetup()
        setup.run()
    except KeyboardInterrupt:
        print("\n\n👋 До свидания!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    main()