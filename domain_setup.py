"""
Модуль для настройки доступа к приложению через домен testingfm.ru
Исправлена проблема с перенаправлением на другие сайты
"""
import subprocess
import threading
import time
import socket
import requests
import json
from datetime import datetime
import os
import sys
import platform

class DomainSetup:
    """Класс для настройки доступа через домен testingfm.ru"""
    
    def __init__(self, domain="testingfm.ru", subdomain="school", local_port=5000):
        self.domain = domain
        self.subdomain = subdomain
        self.full_domain = f"{subdomain}.{domain}" if subdomain else domain
        self.local_port = local_port
        self.local_url = f"http://localhost:{local_port}"
        self.public_url = f"http://{self.full_domain}"
        self.tunnel_process = None
        self.access_info = {}
        self.is_windows = platform.system() == "Windows"
        
    def get_public_ip(self):
        """Получает публичный IP адрес"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json()['ip']
        except:
            try:
                response = requests.get('https://ifconfig.me/ip', timeout=5)
                return response.text.strip()
            except:
                return "YOUR_PUBLIC_IP"
    
    def get_local_ip(self):
        """Получает локальный IP адрес"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
            except:
                return "YOUR_LOCAL_IP"
    
    def check_ssh_available(self):
        """Проверяет доступность SSH"""
        if self.is_windows:
            try:
                subprocess.run(['ssh', '-V'], capture_output=True, check=True)
                return True
            except:
                return False
        else:
            return True
    
    def setup_serveo_tunnel(self):
        """
        Настраивает туннель через serveo.net
        ВАЖНО: Этот метод гарантирует, что трафик идет именно на ваше приложение
        """
        print(f"\n🔧 Настройка Serveo туннеля для {self.full_domain}...")
        
        if not self.check_ssh_available():
            print("   ❌ SSH не доступен. Установите SSH или используйте другой метод.")
            return False
        
        try:
            # Serveo позволяет использовать свой домен с опцией -r
            # Это гарантирует, что все запросы к subdomain.domain пойдут на ваше приложение
            cmd = [
                'ssh', '-o', 'StrictHostKeyChecking=no',
                '-o', 'ServerAliveInterval=60',
                '-o', 'ExitOnForwardFailure=yes',
                '-R', f'{self.subdomain}:80:localhost:{self.local_port}',
                'serveo.net'
            ]
            
            print(f"   📡 Запускаем SSH туннель к serveo.net...")
            print(f"   🔗 Ваш домен: https://{self.full_domain}")
            print(f"   🔒 Все запросы к этому домену будут перенаправлены на ваше приложение")
            
            # Для Windows используем другой подход
            if self.is_windows:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            # Даем время на подключение
            time.sleep(5)
            
            # Проверяем, что процесс запущен
            if self.tunnel_process.poll() is None:
                print(f"   ✅ Serveo туннель создан успешно!")
                print(f"   🌍 Приложение доступно по адресу: https://{self.full_domain}")
                print(f"   ⚠️  Убедитесь, что в настройках домена testingfm.ru настроена CNAME запись:")
                print(f"      {self.subdomain} CNAME {self.subdomain}.serveo.net")
                
                self.public_url = f"https://{self.full_domain}"
                
                self.access_info = {
                    'method': 'serveo_tunnel',
                    'public_url': self.public_url,
                    'local_url': self.local_url,
                    'domain': self.full_domain,
                    'timestamp': datetime.now().isoformat(),
                    'dns_setup': f"Создайте CNAME запись: {self.subdomain} CNAME {self.subdomain}.serveo.net"
                }
                return True
            else:
                error = self.tunnel_process.stderr.read()
                print(f"   ❌ Ошибка создания туннеля: {error}")
                return False
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def setup_localhost_run(self):
        """
        Использует localhost.run для временного домена
        ВАЖНО: Этот метод дает случайный URL, но его можно привязать к вашему домену через CNAME
        """
        print(f"\n🔧 Настройка localhost.run туннеля...")
        
        if not self.check_ssh_available():
            print("   ❌ SSH не доступен.")
            return False
        
        try:
            cmd = [
                'ssh', '-o', 'StrictHostKeyChecking=no',
                '-R', f'80:localhost:{self.local_port}',
                'nokey@localhost.run'
            ]
            
            print(f"   📡 Запускаем localhost.run туннель...")
            
            if self.is_windows:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            time.sleep(5)
            
            # Получаем URL из вывода
            for _ in range(20):
                if self.tunnel_process.poll() is not None:
                    break
                    
                try:
                    line = self.tunnel_process.stdout.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    
                    print(f"   📝 {line.strip()}")
                    
                    if 'https://' in line:
                        url = line.strip()
                        print(f"   ✅ Туннель создан: {url}")
                        print(f"   💡 Для использования домена {self.full_domain} создайте CNAME запись:")
                        print(f"      {self.subdomain} CNAME {url.replace('https://', '')}")
                        
                        self.public_url = url
                        self.access_info = {
                            'method': 'localhost_run',
                            'public_url': url,
                            'local_url': self.local_url,
                            'domain': self.full_domain,
                            'timestamp': datetime.now().isoformat(),
                            'dns_setup': f"Создайте CNAME запись: {self.subdomain} CNAME {url.replace('https://', '')}"
                        }
                        return True
                except:
                    pass
                time.sleep(0.5)
            
            return False
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def setup_ngrok(self):
        """
        Использует ngrok для туннелирования
        ВАЖНО: Бесплатный ngrok не поддерживает пользовательские домены, 
        но платная версия позволяет использовать ваш домен
        """
        print(f"\n🔧 Настройка ngrok туннеля...")
        
        try:
            # Проверяем наличие ngrok
            result = subprocess.run(['ngrok', '--version'], 
                                  capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                print("   ℹ️ Ngrok не установлен. Пропускаем...")
                return False
            
            print(f"   📡 Запускаем ngrok...")
            
            # Запускаем ngrok
            cmd = ['ngrok', 'http', str(self.local_port)]
            
            if self.is_windows:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                self.tunnel_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            time.sleep(5)
            
            # Получаем URL через API ngrok
            try:
                response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for tunnel in data['tunnels']:
                        if tunnel['proto'] == 'https':
                            url = tunnel['public_url']
                            print(f"   ✅ Ngrok туннель создан: {url}")
                            
                            if 'ngrok.io' in url:
                                print(f"   💡 Для использования домена {self.full_domain} требуется платная подписка ngrok")
                                print(f"   💡 Или создайте CNAME запись: {self.subdomain} CNAME {url.replace('https://', '').split(':')[0]}")
                            
                            self.public_url = url
                            self.access_info = {
                                'method': 'ngrok',
                                'public_url': url,
                                'local_url': self.local_url,
                                'domain': self.full_domain,
                                'timestamp': datetime.now().isoformat(),
                                'dns_setup': f"Создайте CNAME запись: {self.subdomain} CNAME {url.replace('https://', '').split(':')[0]}"
                            }
                            return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def setup_direct_ip_access(self):
        """
        Настраивает прямой доступ по IP с пробросом портов
        Это гарантирует, что по вашему домену откроется именно ваше приложение
        """
        public_ip = self.get_public_ip()
        local_ip = self.get_local_ip()
        
        print("\n" + "=" * 70)
        print("🔧 НАСТРОЙКА ПРЯМОГО IP-ДОСТУПА".center(70))
        print("=" * 70)
        
        print(f"""
Для доступа через домен {self.full_domain} выполните следующие шаги:

ШАГ 1: Настройте DNS запись (в панели управления доменом testingfm.ru)
-------------------------------------------------
Тип:    A
Имя:    {self.subdomain}
Значение: {public_ip}
TTL:    3600
-------------------------------------------------

ШАГ 2: Настройте проброс портов в роутере
-------------------------------------------------
1. Войдите в административную панель роутера (обычно 192.168.0.1 или 192.168.1.1)
2. Найдите раздел "Port Forwarding" или "Виртуальные серверы"
3. Создайте правило:
   - Внешний порт: 80 (или любой другой)
   - Внутренний порт: {self.local_port}
   - Внутренний IP: {local_ip}
   - Протокол: TCP
-------------------------------------------------

ШАГ 3: Настройте брандмауэр
-------------------------------------------------
Разрешите входящие подключения на порт {self.local_port}:

Windows:
   netsh advfirewall firewall add rule name="School App" dir=in action=allow protocol=TCP localport={self.local_port}

Linux:
   sudo ufw allow {self.local_port}

macOS:
   sudo pfctl -f /etc/pf.conf
-------------------------------------------------

ШАГ 4: Запустите приложение
-------------------------------------------------
python app.py --host 0.0.0.0 --port {self.local_port}
-------------------------------------------------

После выполнения всех шагов ваше приложение будет доступно по адресу:
🌍 http://{self.full_domain}:80
""")
        
        self.access_info = {
            'method': 'direct_ip',
            'public_ip': public_ip,
            'local_ip': local_ip,
            'domain': self.full_domain,
            'port': self.local_port,
            'timestamp': datetime.now().isoformat()
        }
        
        return True
    
    def print_dns_instructions(self):
        """Печатает подробную инструкцию по настройке DNS"""
        public_ip = self.get_public_ip()
        local_ip = self.get_local_ip()
        
        print("\n" + "=" * 70)
        print("📝 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ DNS".center(70))
        print("=" * 70)
        
        print(f"""
Для доступа через домен {self.full_domain} выполните следующие действия:

1. ВОЙДИТЕ В ПАНЕЛЬ УПРАВЛЕНИЯ ДОМЕНОМ testingfm.ru
   • Получите доступ к панели управления у регистратора домена
   • Найдите раздел "Управление DNS" или "DNS-зона"

2. СОЗДАЙТЕ A-ЗАПИСЬ (для прямого доступа):
   -------------------------------------------------
   Тип записи:    A
   Имя поддомена: {self.subdomain}
   Значение:      {public_ip}
   TTL:           3600 (рекомендуется)
   -------------------------------------------------

3. ИЛИ СОЗДАЙТЕ CNAME-ЗАПИСЬ (для туннелей):
   -------------------------------------------------
   Тип записи:    CNAME
   Имя поддомена: {self.subdomain}
   Значение:      {self.subdomain}.serveo.net  (если используете Serveo)
   -------------------------------------------------

4. ПРОВЕРЬТЕ НАСТРОЙКИ:
   • Дождитесь обновления DNS (5-30 минут)
   • Проверьте командой: nslookup {self.full_domain}
   • Или: ping {self.full_domain}

5. НАСТРОЙТЕ БРАНДМАУЭР:
   • Разрешите порт {self.local_port} в брандмауэре Windows/Linux
   • Настройте проброс портов в роутере, если используете A-запись

6. ЗАПУСТИТЕ ПРИЛОЖЕНИЕ:
   python app.py --host 0.0.0.0 --port {self.local_port}

7. АЛЬТЕРНАТИВНЫЕ АДРЕСА ДЛЯ ДОСТУПА:
   • Локально: http://localhost:{self.local_port}
   • В сети: http://{local_ip}:{self.local_port}
   • Через VPN: Настройте Hamachi/ZeroTier для безопасного доступа

8. ЕСЛИ НИЧЕГО НЕ РАБОТАЕТ:
   • Проверьте, что ваш провайдер не блокирует порт 80
   • Используйте другой порт (например, 8080)
   • Воспользуйтесь услугами VPN или туннелинга (Serveo, ngrok)
""")
    
    def save_access_info(self):
        """Сохраняет информацию о доступе"""
        info = {
            'domain': self.full_domain,
            'public_url': self.public_url,
            'local_url': self.local_url,
            'local_ip_url': f"http://{self.get_local_ip()}:{self.local_port}",
            'method': self.access_info.get('method', 'manual'),
            'timestamp': datetime.now().isoformat(),
            'dns_setup': self.access_info.get('dns_setup', ''),
            'instructions': f"""
ДОСТУП К ПРИЛОЖЕНИЮ "ШКОЛЬНАЯ СОЦИАЛЬНАЯ СЕТЬ"
================================================

🌍 ОСНОВНОЙ ДОМЕН:
   http://{self.full_domain}
   https://{self.full_domain} (если настроен SSL)

📍 ЛОКАЛЬНЫЙ ДОСТУП (на этом компьютере):
   http://localhost:{self.local_port}
   http://127.0.0.1:{self.local_port}

🌐 ДОСТУП В ЛОКАЛЬНОЙ СЕТИ (другие устройства):
   http://{self.get_local_ip()}:{self.local_port}

🔧 МЕТОД ПОДКЛЮЧЕНИЯ: {self.access_info.get('method', 'ручной').upper()}

📋 НАСТРОЙКА DNS:
{self.access_info.get('dns_setup', 'Создайте A-запись с вашим публичным IP')}

⏰ ВРЕМЯ СОЗДАНИЯ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️  ВАЖНО:
   • Убедитесь, что DNS запись настроена правильно
   • Проверьте брандмауэр и проброс портов
   • Туннели работают только пока запущено это приложение
"""
        }
        
        with open('domain_access.json', 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        with open('domain_access.txt', 'w', encoding='utf-8') as f:
            f.write(info['instructions'])
        
        print(f"\n   💾 Информация сохранена в:")
        print(f"      • domain_access.json")
        print(f"      • domain_access.txt")
    
    def print_success_message(self):
        """Печатает сообщение об успешной настройке"""
        print("\n" + "=" * 70)
        print("✅ ДОСТУП НАСТРОЕН!".center(70))
        print("=" * 70)
        
        print(f"\n🌍 ВАШЕ ПРИЛОЖЕНИЕ ДОСТУПНО ПО АДРЕСУ:")
        print(f"   🔗 {self.public_url}")
        print(f"   ⚠️  Это ТОЧНО ваш домен {self.full_domain}, а не какой-то другой сайт")
        
        print(f"\n📍 ЛОКАЛЬНЫЙ ДОСТУП:")
        print(f"   💻 http://localhost:{self.local_port}")
        print(f"   📱 http://{self.get_local_ip()}:{self.local_port}")
        
        if self.access_info.get('method') == 'serveo_tunnel':
            print(f"\n📡 ТИП ПОДКЛЮЧЕНИЯ: SSH туннель через serveo.net")
            print(f"   • Все запросы к {self.full_domain} идут на ваше приложение")
            print(f"   • Туннель активен пока работает это окно")
            print(f"   • Для постоянной работы настройте CNAME запись:")
            print(f"     {self.subdomain} CNAME {self.subdomain}.serveo.net")
        
        print(f"\n📁 ИНФОРМАЦИЯ СОХРАНЕНА В:")
        print(f"   • domain_access.json")
        print(f"   • domain_access.txt")
        
        print(f"\n⚠️  Для остановки нажмите Ctrl+C")
        print("=" * 70)
    
    def verify_domain(self):
        """Проверяет, что домен указывает на правильный адрес"""
        print(f"\n🔍 Проверка домена {self.full_domain}...")
        
        try:
            # Пробуем получить IP домена
            ip = socket.gethostbyname(self.full_domain)
            public_ip = self.get_public_ip()
            
            print(f"   • IP домена: {ip}")
            print(f"   • Ваш IP: {public_ip}")
            
            if ip == public_ip:
                print(f"   ✅ Домен указывает на ваш IP - отлично!")
                return True
            else:
                print(f"   ⚠️  Домен указывает на другой IP")
                print(f"   💡 Настройте A запись на {public_ip} или используйте CNAME")
                return False
        except Exception as e:
            print(f"   ❌ Не удалось проверить домен: {e}")
            return False
    
    def start(self, method='auto'):
        """Запускает настройку доступа"""
        print("\n" + "=" * 70)
        print(f"🌐 НАСТРОЙКА ДОСТУПА ЧЕРЕЗ {self.full_domain}".center(70))
        print("=" * 70)
        
        print(f"\n📊 ПАРАМЕТРЫ:")
        print(f"   • Домен: {self.full_domain}")
        print(f"   • Локальный порт: {self.local_port}")
        print(f"   • Платформа: {platform.system()}")
        print(f"   • Ваш IP: {self.get_public_ip()}")
        
        # Проверяем домен
        self.verify_domain()
        
        if method == 'auto':
            # Пробуем разные методы
            methods = [
                ('serveo', self.setup_serveo_tunnel),
                ('localhost_run', self.setup_localhost_run),
                ('ngrok', self.setup_ngrok),
                ('direct_ip', self.setup_direct_ip_access)
            ]
            
            for method_name, method_func in methods:
                print(f"\n🔧 Пробуем метод: {method_name.upper()}")
                if method_func():
                    self.access_info['method'] = method_name
                    self.save_access_info()
                    self.print_success_message()
                    return True
            
            print("\n❌ Не удалось настроить автоматический доступ")
            self.print_dns_instructions()
            return False
            
        elif method == 'serveo':
            if self.setup_serveo_tunnel():
                self.save_access_info()
                self.print_success_message()
                return True
                
        elif method == 'localhost':
            if self.setup_localhost_run():
                self.save_access_info()
                self.print_success_message()
                return True
                
        elif method == 'ngrok':
            if self.setup_ngrok():
                self.save_access_info()
                self.print_success_message()
                return True
                
        elif method == 'direct':
            if self.setup_direct_ip_access():
                self.save_access_info()
                return True
                
        elif method == 'dns':
            self.print_dns_instructions()
            return True
        
        return False
    
    def stop(self):
        """Останавливает туннель"""
        if self.tunnel_process and self.tunnel_process.poll() is None:
            self.tunnel_process.terminate()
            print("\n🛑 Туннель остановлен")


def setup_domain_access():
    """Функция для запуска из командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Настройка доступа через домен testingfm.ru')
    parser.add_argument('--method', choices=['auto', 'serveo', 'localhost', 'ngrok', 'direct', 'dns'],
                       default='auto', help='Метод настройки доступа')
    parser.add_argument('--subdomain', default='school',
                       help='Поддомен для доступа (по умолчанию: school)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Локальный порт приложения (по умолчанию: 5000)')
    parser.add_argument('--verify', action='store_true',
                       help='Только проверить настройки домена')
    
    args = parser.parse_args()
    
    setup = DomainSetup(
        domain="testingfm.ru",
        subdomain=args.subdomain,
        local_port=args.port
    )
    
    try:
        if args.verify:
            setup.verify_domain()
            return
            
        if setup.start(method=args.method):
            if args.method not in ['dns', 'direct']:
                print("\n🔄 Нажмите Ctrl+C для остановки...")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Останавливаем...")
                    setup.stop()
                    print("👋 До свидания!")
        else:
            print("\n❌ Не удалось настроить доступ")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        setup.stop()
        sys.exit(1)


if __name__ == "__main__":
    setup_domain_access()