from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(300))
    file_path = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    hashtags = db.relationship('Hashtag', secondary='post_hashtags', backref=db.backref('posts', lazy=True))
    author = db.relationship('User', backref=db.backref('posts', lazy=True))

class Hashtag(db.Model):
    __tablename__ = 'hashtags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    popularity = db.Column(db.Integer, default=0)

class PostHashtag(db.Model):
    __tablename__ = 'post_hashtags'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    hashtag_id = db.Column(db.Integer, db.ForeignKey('hashtags.id'), nullable=False)

class Friendship(db.Model):
    __tablename__ = 'friendships'
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user1_id', 'user2_id', name='unique_friendship'),
    )

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_group = db.Column(db.Boolean, default=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True))
    group = db.relationship('Group', backref=db.backref('messages', lazy=True))

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    class_name = db.Column(db.String(20))
    is_class_group = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref=db.backref('created_groups', lazy=True))

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', name='unique_group_member'),
    )

class GroupJoinRequest(db.Model):
    __tablename__ = 'group_join_requests'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', name='unique_join_request'),
    )