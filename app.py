"""
Школьная социальная сеть
Домен: testingfm.ru
Сервер: 178.212.250.85
Порт: 5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import db, Post, Hashtag, PostHashtag, Friendship, Message, Group, GroupMember, GroupJoinRequest
from models import User
from datetime import datetime
import os
from PIL import Image
from sqlalchemy import or_
import re
from sqlalchemy.exc import IntegrityError

import argparse

# Импорты для автоматической настройки и live render
import socket, threading, subprocess, json, sys, platform

# ==================== ИНИЦИАЛИЗАЦИЯ FLASK ===================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_FILE_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Константы сервера
SERVER_IP = "178.212.250.85"
DOMAIN = "testingfm.ru"
WWW_DOMAIN = f"www.{DOMAIN}"
DEFAULT_PORT = 5000

# ==================== КЛАСС АВТОМАТИЧЕСКОЙ НАСТРОЙКИ ====================

class AutoDomainSetup:
    """Автоматическая настройка домена testingfm.ru"""
    
    def __init__(self):
        self.domain = DOMAIN
        self.www_domain = WWW_DOMAIN
        self.server_ip = SERVER_IP
        self.port = DEFAULT_PORT
        self.local_ip = self.get_local_ip()
        self.public_ip = self.server_ip
        self.auto_start_file = self.get_auto_start_file()
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def get_auto_start_file(self):
        try:
            if self.is_windows:
                startup_folder = os.path.join(os.environ['APPDATA'], 
                                             'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
                return os.path.join(startup_folder, 'school_app.bat')
            elif self.is_macos:
                return os.path.expanduser('~/Library/LaunchAgents/com.schoolapp.plist')
            elif self.is_linux:
                return os.path.expanduser('~/.config/autostart/school-app.desktop')
        except:
            return None
    
    def check_port_open(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.server_ip, self.port))
            sock.close()
            return result == 0
        except:
            return False

    def save_config(self):
        config = {
            'domain': self.domain,
            'www_domain': self.www_domain,
            'server_ip': self.server_ip,
            'port': self.port,
            'local_ip': self.local_ip,
            'urls': {
                'main': f'http://{self.domain}:{self.port}',
                'www': f'http://{self.www_domain}:{self.port}',
                'direct': f'http://{self.server_ip}:{self.port}',
                'local': f'http://localhost:{self.port}',
                'network': f'http://{self.local_ip}:{self.port}'
            }
        }
        with open('testingfm_auto_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_hashtags(text):
    return list(set(re.findall(r'#(\w+)', text)))

def process_hashtags(content, post):
    try:
        hashtag_names = extract_hashtags(content)
        for tag_name in hashtag_names:
            hashtag = Hashtag.query.filter_by(name=tag_name).first()
            if not hashtag:
                hashtag = Hashtag(name=tag_name, popularity=1)
                db.session.add(hashtag)
                try: db.session.commit()
                except: db.session.rollback()
            else:
                hashtag.popularity = (hashtag.popularity or 0) + 1
            if not PostHashtag.query.filter_by(post_id=post.id, hashtag_id=hashtag.id).first():
                db.session.add(PostHashtag(post_id=post.id, hashtag_id=hashtag.id))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка хештегов: {e}")

def create_upload_folders():
    for folder in ['images', 'files']:
        path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(path, exist_ok=True)
        
# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

@app.route('/')
def index():
    """Главная страница"""
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    
    popular_hashtags = Hashtag.query.order_by(Hashtag.popularity.desc()).limit(10).all()
    
    return render_template('index.html', posts=posts, popular_hashtags=popular_hashtags, now=datetime.now)


@app.route('/search')
@login_required
def search():
    """Поиск постов, пользователей и хештегов"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'posts')
    
    results = []
    
    if search_type == 'posts':
        results = Post.query.filter(
            or_(
                Post.title.ilike(f'%{query}%'),
                Post.content.ilike(f'%{query}%')
            )
        ).order_by(Post.created_at.desc()).all()
    
    elif search_type == 'users':
        results = User.query.filter(
            or_(
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
                User.class_name.ilike(f'%{query}%')
            )
        ).filter(User.id != current_user.id).all()
    
    elif search_type == 'hashtags':
        hashtag = Hashtag.query.filter(Hashtag.name.ilike(f'%{query}%')).first()
        if hashtag:
            results = Post.query.join(PostHashtag).filter(
                PostHashtag.hashtag_id == hashtag.id
            ).order_by(Post.created_at.desc()).all()
    
    return render_template('search.html', 
                         query=query, 
                         search_type=search_type, 
                         results=results)


@app.route('/find_friends')
@login_required
def find_friends():
    """Поиск друзей"""
    query = request.args.get('q', '')
    
    if query:
        users = User.query.filter(
            or_(
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%'),
                User.class_name.ilike(f'%{query}%')
            )
        ).filter(User.id != current_user.id).all()
    else:
        users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('find_friends.html', users=users, query=query)


@app.route('/forward_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def forward_post(post_id):
    """Пересылка поста в группу"""
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        message_text = request.form.get('message', '')
        
        if not group_id:
            flash('Выберите группу для пересылки')
            return redirect(url_for('forward_post', post_id=post_id))
        
        group = Group.query.get_or_404(group_id)
        
        if not group.is_class_group:
            is_member = GroupMember.query.filter_by(
                group_id=group_id, 
                user_id=current_user.id
            ).first()
            if not is_member:
                flash('Вы не состоите в этой группе')
                return redirect(url_for('forward_post', post_id=post_id))
        
        forward_content = f"📨 Переслано: {post.title}\n\n"
        if message_text:
            forward_content += f"💬 {message_text}\n\n"
        forward_content += f"📝 {post.content[:500]}"
        if len(post.content) > 500:
            forward_content += "..."
        
        if post.image_path:
            forward_content += "\n\n🖼️ [Прикреплено изображение]"
        
        if post.file_path:
            forward_content += "\n\n📎 [Прикреплен файл]"
        
        message = Message(
            sender_id=current_user.id,
            group_id=group_id,
            content=forward_content,
            is_group=True
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash(f'Пост переслан в группу "{group.name}"')
        return redirect(url_for('group_chat', group_id=group_id))
    
    user_groups = Group.query.join(GroupMember).filter(
        GroupMember.user_id == current_user.id
    ).all()
    
    class_groups = Group.query.filter_by(
        class_name=current_user.class_name, 
        is_class_group=True
    ).all()
    
    available_groups = list(set(user_groups + class_groups))
    
    return render_template('forward_post.html', 
                         post=post, 
                         groups=available_groups)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверная почта или пароль', 'danger')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        class_name = request.form.get('class_name')
        
        if not all([email, password, first_name, last_name, class_name]):
            flash('Все поля обязательны для заполнения', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с такой почтой уже существует', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            email=email,
            password=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            class_name=class_name
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь войдите в аккаунт.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    """Создание нового поста"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        is_anonymous = 'is_anonymous' in request.form
        
        if not title and not content:
            flash('Пост должен содержать заголовок или содержание', 'danger')
            return redirect(url_for('create_post'))
        
        post = Post(
            title=title,
            content=content,
            is_anonymous=is_anonymous,
            user_id=current_user.id
        )
        
        if 'image' in request.files:
            image = request.files['image']
            if image and image.filename and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
                filename = secure_filename(f"{datetime.now().timestamp()}_{image.filename}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', filename)
                
                try:
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    img = Image.open(image)
                    img.thumbnail((800, 800))
                    img.save(image_path)
                    post.image_path = f'images/{filename}'
                except Exception as e:
                    flash(f'Ошибка при обработке изображения: {str(e)}', 'warning')
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename, ALLOWED_FILE_EXTENSIONS):
                filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'files', filename)
                
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                
                post.file_path = f'files/{filename}'
        
        db.session.add(post)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании поста: {str(e)}', 'danger')
            return redirect(url_for('create_post'))
        
        try:
            process_hashtags(content, post)
        except Exception as e:
            flash(f'Ошибка при обработке хештегов: {str(e)}', 'warning')
        
        flash('Пост успешно создан!', 'success')
        return redirect(url_for('index'))
    
    return render_template('create_post.html')


@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    """Удаление поста"""
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        flash('Вы не можете удалить этот пост', 'danger')
        return redirect(url_for('index'))
    
    try:
        hashtags = Hashtag.query.join(PostHashtag).filter(
            PostHashtag.post_id == post_id
        ).all()
        
        for hashtag in hashtags:
            if hashtag.popularity and hashtag.popularity > 0:
                hashtag.popularity -= 1
        
        PostHashtag.query.filter_by(post_id=post_id).delete()
        
        db.session.delete(post)
        db.session.commit()
        
        flash('Пост удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении поста: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('index'))


@app.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(
        Post.created_at.desc()
    ).all()
    
    friendships = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) | (Friendship.user2_id == current_user.id)) &
        (Friendship.status == 'accepted')
    ).all()
    
    friends = []
    for friendship in friendships:
        if friendship.user1_id == current_user.id:
            friend = User.query.get(friendship.user2_id)
        else:
            friend = User.query.get(friendship.user1_id)
        if friend:
            friends.append(friend)
    
    incoming_requests = Friendship.query.filter(
        (Friendship.user2_id == current_user.id) & 
        (Friendship.status == 'pending')
    ).all()
    
    incoming_users = []
    for request in incoming_requests:
        user = User.query.get(request.user1_id)
        if user:
            incoming_users.append({'user': user, 'friendship_id': request.id})
    
    return render_template('profile.html', 
                         user_posts=user_posts, 
                         friends=friends,
                         incoming_requests=incoming_users)


@app.route('/classmates')
@login_required
def classmates():
    """Одноклассники"""
    classmates = User.query.filter_by(class_name=current_user.class_name).all()
    return render_template('classmates.html', classmates=classmates)


@app.route('/friends')
@login_required
def friends():
    """Список друзей"""
    friendships = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) | (Friendship.user2_id == current_user.id)) &
        (Friendship.status == 'accepted')
    ).all()
    
    friends = []
    for friendship in friendships:
        if friendship.user1_id == current_user.id:
            friend = User.query.get(friendship.user2_id)
        else:
            friend = User.query.get(friendship.user1_id)
        if friend:
            friends.append(friend)
    
    incoming_requests = Friendship.query.filter(
        (Friendship.user2_id == current_user.id) & 
        (Friendship.status == 'pending')
    ).all()
    
    incoming_users = []
    for request in incoming_requests:
        user = User.query.get(request.user1_id)
        if user:
            incoming_users.append({'user': user, 'friendship_id': request.id})
    
    outgoing_requests = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) & 
        (Friendship.status == 'pending')
    ).all()
    
    outgoing_users = []
    for request in outgoing_requests:
        user = User.query.get(request.user2_id)
        if user:
            outgoing_users.append(user)
    
    return render_template('friends.html', 
                         friends=friends,
                         incoming_requests=incoming_users,
                         outgoing_requests=outgoing_users)


@app.route('/add_friend/<int:user_id>')
@login_required
def add_friend(user_id):
    """Отправка запроса в друзья"""
    if user_id == current_user.id:
        flash('Нельзя добавить себя в друзья', 'warning')
        return redirect(request.referrer or url_for('find_friends'))
    
    existing_friendship = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == user_id)) |
        ((Friendship.user1_id == user_id) & (Friendship.user2_id == current_user.id))
    ).first()
    
    if existing_friendship:
        if existing_friendship.status == 'pending':
            flash('Запрос в друзья уже отправлен', 'info')
        else:
            flash('Пользователь уже у вас в друзьях', 'info')
    else:
        friendship = Friendship(
            user1_id=current_user.id, 
            user2_id=user_id, 
            status='pending'
        )
        db.session.add(friendship)
        db.session.commit()
        flash('Запрос в друзья отправлен', 'success')
    
    return redirect(request.referrer or url_for('find_friends'))


@app.route('/accept_friend/<int:friendship_id>')
@login_required
def accept_friend(friendship_id):
    """Принятие запроса в друзья"""
    friendship = Friendship.query.get_or_404(friendship_id)
    
    if friendship.user2_id != current_user.id:
        flash('Нельзя принять эту заявку', 'danger')
        return redirect(url_for('friends'))
    
    friendship.status = 'accepted'
    db.session.commit()
    
    flash('Заявка в друзья принята', 'success')
    return redirect(url_for('friends'))


@app.route('/reject_friend/<int:friendship_id>')
@login_required
def reject_friend(friendship_id):
    """Отклонение запроса в друзья"""
    friendship = Friendship.query.get_or_404(friendship_id)
    
    if friendship.user2_id != current_user.id:
        flash('Нельзя отклонить эту заявку', 'danger')
        return redirect(url_for('friends'))
    
    db.session.delete(friendship)
    db.session.commit()
    
    flash('Заявка в друзья отклонена', 'info')
    return redirect(url_for('friends'))


@app.route('/remove_friend/<int:user_id>')
@login_required
def remove_friend(user_id):
    """Удаление из друзей"""
    friendship = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == user_id)) |
        ((Friendship.user1_id == user_id) & (Friendship.user2_id == current_user.id))
    ).first()
    
    if friendship and friendship.status == 'accepted':
        db.session.delete(friendship)
        db.session.commit()
        flash('Пользователь удален из друзей', 'info')
    else:
        flash('Дружба не найдена', 'warning')
    
    return redirect(url_for('friends'))


@app.route('/chat/<int:friend_id>')
@login_required
def chat(friend_id):
    """Личный чат с другом"""
    friend = User.query.get_or_404(friend_id)
    
    friendship = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == friend_id)) |
        ((Friendship.user1_id == friend_id) & (Friendship.user2_id == current_user.id)),
        Friendship.status == 'accepted'
    ).first()
    
    if not friendship:
        flash('Вы не дружите с этим пользователем', 'danger')
        return redirect(url_for('friends'))
    
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id)) |
        ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id)),
        Message.is_group == False
    ).order_by(Message.created_at.asc()).all()
    
    return render_template('chat.html', friend=friend, messages=messages)


@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    """Отправка личного сообщения"""
    receiver_id = request.form.get('receiver_id')
    content = request.form.get('content', '').strip()
    
    if not receiver_id or not content:
        return jsonify({'success': False, 'error': 'Неверные данные'})
    
    friendship = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == receiver_id)) |
        ((Friendship.user1_id == receiver_id) & (Friendship.user2_id == current_user.id)),
        Friendship.status == 'accepted'
    ).first()
    
    if not friendship:
        return jsonify({'success': False, 'error': 'Вы не дружите с этим пользователем'})
    
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        is_group=False
    )
    
    try:
        db.session.add(message)
        db.session.commit()
        return jsonify({'success': True, 'message_id': message.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/groups')
@login_required
def groups():
    """Список групп"""
    user_groups = Group.query.join(GroupMember).filter(
        GroupMember.user_id == current_user.id
    ).all()
    
    class_groups = Group.query.filter_by(
        class_name=current_user.class_name, 
        is_class_group=True
    ).all()
    
    public_groups = Group.query.filter(
        Group.is_public == True,
        Group.is_class_group == False,
        ~Group.id.in_([g.id for g in user_groups])
    ).all()
    
    closed_groups = Group.query.filter(
        Group.is_public == False,
        Group.is_class_group == False,
        ~Group.id.in_([g.id for g in user_groups])
    ).all()
    
    requested_group_ids = []
    for group in closed_groups:
        request = GroupJoinRequest.query.filter_by(
            group_id=group.id,
            user_id=current_user.id,
            status='pending'
        ).first()
        if request:
            requested_group_ids.append(group.id)
    
    return render_template('groups.html', 
                         user_groups=user_groups,
                         class_groups=class_groups,
                         public_groups=public_groups,
                         closed_groups=closed_groups,
                         requested_group_ids=requested_group_ids)


@app.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    """Создание новой группы"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public = request.form.get('is_public') == 'true'
        is_class_group = 'is_class_group' in request.form
        
        if not name:
            flash('Название группы обязательно', 'danger')
            return redirect(url_for('create_group'))
        
        group = Group(
            name=name,
            description=description,
            is_public=is_public,
            is_class_group=is_class_group,
            class_name=current_user.class_name if is_class_group else None,
            created_by=current_user.id
        )
        
        db.session.add(group)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании группы: {str(e)}', 'danger')
            return redirect(url_for('create_group'))
        
        member = GroupMember(group_id=group.id, user_id=current_user.id)
        db.session.add(member)
        
        if is_class_group:
            classmates = User.query.filter_by(
                class_name=current_user.class_name
            ).filter(User.id != current_user.id).all()
            
            for classmate in classmates:
                member = GroupMember(group_id=group.id, user_id=classmate.id)
                db.session.add(member)
        
        try:
            db.session.commit()
            flash('Группа успешно создана!', 'success')
            return redirect(url_for('groups'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении участников: {str(e)}', 'danger')
            return redirect(url_for('create_group'))
    
    return render_template('create_group.html')


@app.route('/join_group/<int:group_id>')
@login_required
def join_group(group_id):
    """Вступление в группу"""
    group = Group.query.get_or_404(group_id)
    
    existing_member = GroupMember.query.filter_by(
        group_id=group_id, 
        user_id=current_user.id
    ).first()
    
    if existing_member:
        flash('Вы уже состоите в этой группе', 'info')
        return redirect(url_for('groups'))
    
    if group.is_public or group.is_class_group:
        member = GroupMember(group_id=group_id, user_id=current_user.id)
        db.session.add(member)
        db.session.commit()
        
        flash(f'Вы вступили в группу "{group.name}"', 'success')
        return redirect(url_for('group_chat', group_id=group_id))
    
    else:
        existing_request = GroupJoinRequest.query.filter_by(
            group_id=group_id,
            user_id=current_user.id,
            status='pending'
        ).first()
        
        if existing_request:
            flash('Заявка на вступление уже отправлена', 'info')
        else:
            request = GroupJoinRequest(
                group_id=group_id,
                user_id=current_user.id,
                status='pending'
            )
            db.session.add(request)
            db.session.commit()
            
            flash('Заявка на вступление отправлена', 'success')
    
    return redirect(url_for('groups'))


@app.route('/cancel_join_request/<int:group_id>')
@login_required
def cancel_join_request(group_id):
    """Отмена заявки на вступление"""
    join_request = GroupJoinRequest.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        status='pending'
    ).first()
    
    if join_request:
        db.session.delete(join_request)
        db.session.commit()
        flash('Заявка на вступление отменена', 'info')
    else:
        flash('Заявка не найдена', 'warning')
    
    return redirect(url_for('groups'))


@app.route('/leave_group/<int:group_id>')
@login_required
def leave_group(group_id):
    """Выход из группы"""
    group = Group.query.get_or_404(group_id)
    
    member = GroupMember.query.filter_by(
        group_id=group_id, 
        user_id=current_user.id
    ).first()
    
    if not member:
        flash('Вы не состоите в этой группе', 'warning')
        return redirect(url_for('groups'))
    
    if group.created_by == current_user.id:
        flash('Создатель группы не может покинуть её', 'danger')
        return redirect(url_for('group_chat', group_id=group_id))
    
    db.session.delete(member)
    db.session.commit()
    
    flash(f'Вы покинули группу "{group.name}"', 'info')
    return redirect(url_for('groups'))


@app.route('/group_chat/<int:group_id>')
@login_required
def group_chat(group_id):
    """Групповой чат"""
    group = Group.query.get_or_404(group_id)
    
    if not group.is_class_group:
        is_member = GroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id
        ).first()
        if not is_member:
            flash('Вы не состоите в этой группе', 'danger')
            return redirect(url_for('groups'))
    
    messages = Message.query.filter_by(
        group_id=group_id, 
        is_group=True
    ).order_by(Message.created_at.asc()).all()
    
    members = User.query.join(GroupMember).filter(
        GroupMember.group_id == group_id
    ).all()
    
    join_requests = []
    if group.created_by == current_user.id and not group.is_public and not group.is_class_group:
        join_requests = GroupJoinRequest.query.filter_by(
            group_id=group_id,
            status='pending'
        ).all()
    
    return render_template('group_chat.html', 
                         group=group, 
                         messages=messages, 
                         members=members,
                         join_requests=join_requests)


@app.route('/send_group_message', methods=['POST'])
@login_required
def send_group_message():
    """Отправка сообщения в группу"""
    group_id = request.form.get('group_id')
    content = request.form.get('content', '').strip()
    
    if not group_id or not content:
        return jsonify({'success': False, 'error': 'Неверные данные'})
    
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'success': False, 'error': 'Группа не найдена'})
    
    if not group.is_class_group:
        is_member = GroupMember.query.filter_by(
            group_id=group_id, 
            user_id=current_user.id
        ).first()
        if not is_member:
            return jsonify({'success': False, 'error': 'Вы не состоите в этой группе'})
    
    message = Message(
        sender_id=current_user.id,
        group_id=group_id,
        content=content,
        is_group=True
    )
    
    try:
        db.session.add(message)
        db.session.commit()
        return jsonify({'success': True, 'message_id': message.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/group_requests/<int:group_id>')
@login_required
def group_requests(group_id):
    """Список заявок на вступление"""
    group = Group.query.get_or_404(group_id)
    
    if group.created_by != current_user.id:
        flash('Только создатель группы может просматривать заявки', 'danger')
        return redirect(url_for('group_chat', group_id=group_id))
    
    join_requests = GroupJoinRequest.query.filter_by(
        group_id=group_id,
        status='pending'
    ).all()
    
    return render_template('group_requests.html', 
                         group=group, 
                         join_requests=join_requests)


@app.route('/handle_group_request/<int:request_id>/<action>')
@login_required
def handle_group_request(request_id, action):
    """Обработка заявки на вступление"""
    join_request = GroupJoinRequest.query.get_or_404(request_id)
    group = Group.query.get_or_404(join_request.group_id)
    
    if group.created_by != current_user.id:
        flash('Только создатель группы может обрабатывать заявки', 'danger')
        return redirect(url_for('group_chat', group_id=group.id))
    
    try:
        if action == 'accept':
            member = GroupMember(
                group_id=group.id,
                user_id=join_request.user_id
            )
            db.session.add(member)
            join_request.status = 'accepted'
            db.session.commit()
            flash('Пользователь принят в группу', 'success')
        
        elif action == 'reject':
            db.session.delete(join_request)
            db.session.commit()
            flash('Заявка отклонена', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обработке заявки: {str(e)}', 'danger')
    
    return redirect(url_for('group_requests', group_id=group.id))


@app.route('/status')
def status():
    """Страница статуса для проверки работы сайта"""
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = '127.0.0.1'
    
    return jsonify({
        'status': 'online',
        'domain': DOMAIN,
        'server_ip': SERVER_IP,
        'time': datetime.now().isoformat(),
        'message': 'Сайт работает!',
        'local_ip': local_ip,
        'port': DEFAULT_PORT,
        'urls': {
            'main': f'http://{DOMAIN}:{DEFAULT_PORT}',
            'www': f'http://{WWW_DOMAIN}:{DEFAULT_PORT}',
            'direct': f'http://{SERVER_IP}:{DEFAULT_PORT}',
            'local': f'http://localhost:{DEFAULT_PORT}'
        }
    })


# ==================== ТОЧКА ВХОДА ====================

def main():
    """Основная функция запуска"""
    parser = argparse.ArgumentParser(description='Школьная социальная сеть')
    parser.add_argument('--port', type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    parser.add_argument('--host', default='0.0.0.0', help='Хост для запуска')
    parser.add_argument('--auto-setup', action='store_true', help='Автоматическая настройка')
    parser.add_argument('--auto-run', action='store_true', help='Запуск без интерактива')
    parser.add_argument('--no-setup', action='store_true', help='Пропустить настройку')
    
    args = parser.parse_args()
    
    setup_instance = None
    
    try:
        # Создаем папки и базу данных
        with app.app_context():
            db.create_all()
            create_upload_folders()
        
        # Автоматическая настройка
        if not args.no_setup and (args.auto_setup or not os.path.exists('testingfm_auto_config.json')):
            setup_instance = AutoDomainSetup()
            setup_instance.port = args.port
            
            try:
                setup_instance.run_auto_setup()
            except KeyboardInterrupt:
                print("\n\n⚠️ Настройка прервана пользователем")
                if setup_instance:
                    setup_instance.cleanup()
        
        # Запуск сервера
        print(f"\n{'='*50}")
        print(f"🚀 ЗАПУСК СЕРВЕРА НА ПОРТУ {args.port}")
        print(f"{'='*50}")
        print(f"\n📍 Локальный доступ: http://localhost:{args.port}")
        
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            print(f"📱 В сети: http://{local_ip}:{args.port}")
        except:
            pass
        
        print(f"🌍 Домен: http://{DOMAIN}:{args.port}")
        print(f"🌐 IP: http://{SERVER_IP}:{args.port}")
        print(f"\n📝 Для проверки статуса: http://localhost:{args.port}/status")
        print(f"⚠️  Нажмите Ctrl+C для остановки сервера\n")
        
        app.run(
            host=args.host,
            port=args.port,
            debug=True,
            threaded=True,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 Сервер остановлен пользователем")
        if setup_instance:
            setup_instance.cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        if setup_instance:
            setup_instance.cleanup()
        sys.exit(1)


if __name__ == '__main__':
    create_upload_folders()
    auto_setup = AutoDomainSetup()
    auto_setup.save_config()
    app.run(host='0.0.0.0', port=DEFAULT_PORT, debug=True, use_reloader=True)