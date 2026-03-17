from flask_login import UserMixin
from database import db
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношения - ИСПРАВЛЕНО: добавлены отсутствующие связи
    sent_friendships = db.relationship('Friendship', 
                                        foreign_keys='Friendship.user1_id',
                                        backref='user1', lazy=True)
    received_friendships = db.relationship('Friendship',
                                          foreign_keys='Friendship.user2_id',
                                          backref='user2', lazy=True)
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def is_friend_with(self, other_user):
        from database import Friendship
        friendship = Friendship.query.filter(
            ((Friendship.user1_id == self.id) & (Friendship.user2_id == other_user.id)) |
            ((Friendship.user1_id == other_user.id) & (Friendship.user2_id == self.id)),
            Friendship.status == 'accepted'
        ).first()
        return friendship is not None
    
    def get_friendship_status(self, other_user):
        from database import Friendship
        friendship = Friendship.query.filter(
            ((Friendship.user1_id == self.id) & (Friendship.user2_id == other_user.id)) |
            ((Friendship.user1_id == other_user.id) & (Friendship.user2_id == self.id))
        ).first()
        
        if not friendship:
            return None
        
        if friendship.status == 'accepted':
            return 'accepted'
        elif friendship.user1_id == self.id:
            return 'pending_sent'
        else:
            return 'pending_received'