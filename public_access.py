import socket
import threading
import requests
import json
import time
from datetime import datetime
import sys
from urllib.parse import urlparse

class PublicAccessServer:
    def __init__(self, local_port=5000, proxy_port=8080):
        self.local_port = local_port
        self.proxy_port = proxy_port
        self.local_url = f"http://localhost:{local_port}"
        self.proxy_url = None
        self.server = None
        self.running = False
        
    def get_public_ip(self):
        """Получает публичный IP адрес"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json()['ip']
        except:
            return None
    
    def start_proxy_server(self):
        """Запускает простой прокси-сервер"""
        import http.server
        import socketserver
        import urllib.request
        
        class ProxyHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    # Проксируем запрос на локальный сервер
                    url = f"http://localhost:{self.local_port}{self.path}"
                    req = urllib.request.Request(url)
                    
                    with urllib.request.urlopen(req) as response:
                        self.send_response(response.status)
                        for header, value in response.headers.items():
                            self.send_header(header, value)
                        self.end_headers()
                        self.wfile.write(response.read())
                except Exception as e:
                    self.send_error(500, str(e))
            
            def do_POST(self):
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    url = f"http://localhost:{self.local_port}{self.path}"
                    req = urllib.request.Request(url, data=post_data)
                    
                    for header, value in self.headers.items():
                        if header.lower() not in ['host', 'content-length']:
                            req.add_header(header, value)
                    
                    with urllib.request.urlopen(req) as response:
                        self.send_response(response.status)
                        for header, value in response.headers.items():
                            self.send_header(header, value)
                        self.end_headers()
                        self.wfile.write(response.read())
                except Exception as e:
                    self.send_error(500, str(e))
            
            def log_message(self, format, *args):
                # Отключаем стандартное логирование
                pass
        
        # Запуск прокси-сервера
        with socketserver.TCPServer(("", self.proxy_port), ProxyHandler) as httpd:
            print(f"🌐 Прокси-сервер запущен на порту {self.proxy_port}")
            self.server = httpd
            self.running = True
            httpd.serve_forever()
    
    def configure_port_forwarding(self):
        """Настраивает перенаправление портов"""
        print("🔧 Настройка перенаправления портов...")
        
        public_ip = self.get_public_ip()
        if public_ip:
            print(f"📍 Ваш публичный IP: {public_ip}")
            print(f"🌐 Для доступа используйте: http://{public_ip}:{self.proxy_port}")
            self.proxy_url = f"http://{public_ip}:{self.proxy_port}"
            return True
        else:
            print("⚠️  Не удалось определить публичный IP")
            return False
    
    def print_access_info(self):
        """Печатает информацию для доступа"""
        print("\n" + "=" * 50)
        print("🌐 ИНФОРМАЦИЯ ДЛЯ ДОСТУПА")
        print("=" * 50)
        
        # Локальные адреса
        print("\n📍 Локальный доступ:")
        print(f"   • http://localhost:{self.local_port}")
        print(f"   • http://127.0.0.1:{self.local_port}")
        
        # Сетевые адреса
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"\n🌐 Доступ в локальной сети:")
            print(f"   • http://{local_ip}:{self.local_port}")
        except:
            pass
        
        # Публичный доступ
        if self.proxy_url:
            print(f"\n🌍 Публичный доступ:")
            print(f"   • {self.proxy_url}")
            
            # Генерируем QR код
            self.print_qr_code(self.proxy_url)
        
        print("\n⚠️  Для публичного доступа нужно настроить:")
        print("   1. Проброс портов в роутере")
        print("   2. Разрешить порт в брандмауэре")
        print("=" * 50)
    
    def print_qr_code(self, url):
        """Печатает QR код"""
        try:
            import qrcode
            qr = qrcode.QRCode()
            qr.add_data(url)
            qr.make()
            
            print("\n📱 QR код для быстрого доступа:")
            qr.print_ascii(invert=True)
        except:
            print("\n📱 QR код недоступен (установите qrcode: pip install qrcode[pil])")
    
    def start(self):
        """Запускает все компоненты"""
        print("🚀 Настройка публичного доступа...")
        
        # Получаем публичный IP
        public_ip = self.get_public_ip()
        if not public_ip:
            print("❌ Не удалось получить публичный IP")
            return False
        
        # Запускаем прокси в отдельном потоке
        proxy_thread = threading.Thread(target=self.start_proxy_server, daemon=True)
        proxy_thread.start()
        
        time.sleep(2)  # Даем время на запуск
        
        self.proxy_url = f"http://{public_ip}:{self.proxy_port}"
        
        # Сохраняем информацию в файл
        self.save_config()
        
        # Печатаем информацию
        self.print_access_info()
        
        print(f"\n⏰ Сервер запущен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔄 Нажмите Ctrl+C для остановки")
        
        # Бесконечный цикл
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Останавливаем сервер...")
            self.stop()
        
        return True
    
    def save_config(self):
        """Сохраняет конфигурацию в файл"""
        config = {
            'local_port': self.local_port,
            'proxy_port': self.proxy_port,
            'proxy_url': self.proxy_url,
            'public_ip': self.get_public_ip(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open('access_config.json', 'w') as f:
            json.dump(config, f, indent=2)
    
    def stop(self):
        """Останавливает сервер"""
        self.running = False
        if self.server:
            self.server.shutdown()

def check_dependencies():
    """Проверяет необходимые зависимости"""
    try:
        import qrcode
        print("✅ qrcode установлен")
    except ImportError:
        print("⚠️  Для QR кодов установите: pip install qrcode[pil]")
    
    try:
        import requests
        print("✅ requests установлен")
    except ImportError:
        print("❌ Установите requests: pip install requests")

def main():
    """Основная функция"""
    print("=" * 60)
    print("🌍 PUBLIC ACCESS SERVER - доступ с любого устройства")
    print("=" * 60)
    
    # Проверка зависимостей
    check_dependencies()
    print("-" * 60)
    
    # Конфигурация
    LOCAL_PORT = 5000  # Порт Flask приложения
    PROXY_PORT = 8080  # Порт для публичного доступа
    
    # Создаем и запускаем сервер
    server = PublicAccessServer(
        local_port=LOCAL_PORT,
        proxy_port=PROXY_PORT
    )
    
    try:
        server.start()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()