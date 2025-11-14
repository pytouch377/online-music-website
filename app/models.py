from datetime import datetime, timedelta, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    
    # 新增个人资料字段
    bio = db.Column(db.Text)  # 个人简介
    avatar = db.Column(db.String(200))  # 头像路径
    location = db.Column(db.String(100))  # 所在地
    website = db.Column(db.String(200))  # 个人网站
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    playlists = db.relationship('Playlist', backref='creator', lazy='dynamic')
    uploaded_songs = db.relationship('Song', backref='uploader', lazy='dynamic')
    
    # 新增社交关系
    followers = db.relationship('Follow',
                               foreign_keys='Follow.followed_id',
                               backref=db.backref('followed', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    
    following = db.relationship('Follow',
                               foreign_keys='Follow.follower_id',
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def follow(self, user):
        if not self.is_following(user):
            follow = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(follow)
    
    def unfollow(self, user):
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
    
    def is_following(self, user):
        return self.following.filter_by(followed_id=user.id).first() is not None
    
    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None
    
    # 获取用户的公开音乐数量
    def get_public_songs_count(self):
        return Song.query.filter_by(user_id=self.id, visibility='public').count()
    
    # 获取用户的公开播放列表数量
    def get_public_playlists_count(self):
        return Playlist.query.filter_by(user_id=self.id, visibility='public').count()
    
    # 获取粉丝数量
    def get_followers_count(self):
        return self.followers.count()
    
    # 获取关注数量
    def get_following_count(self):
        return self.following.count()
    
    def __repr__(self):
        return f'<User {self.username}>'

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    album = db.Column(db.String(100))
    genre = db.Column(db.String(50))
    file_path = db.Column(db.String(200), nullable=False)
    cover_image = db.Column(db.String(200))
    duration = db.Column(db.Integer)  # 时长(秒)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # 新增字段
    visibility = db.Column(db.String(20), default='public')  # public, private
    play_count = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    
    # 关系
    playlist_items = db.relationship('PlaylistItem', backref='song', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='song', lazy='dynamic')
    comments = db.relationship('Comment', backref='song', lazy='dynamic')
    
    def __repr__(self):
        return f'<Song {self.title} by {self.artist}>'

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    visibility = db.Column(db.String(20), default='public')  # public, private
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # 关系
    items = db.relationship('PlaylistItem', backref='playlist', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Playlist {self.name}>'

class PlaylistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'))
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<PlaylistItem {self.id}>'

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Favorite user:{self.user_id} song:{self.song_id}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
    
    @property
    def local_created_at(self):
        """Return created_at converted from UTC to Asia/Shanghai (UTC+8) for display."""
        if self.created_at is None:
            return None
        # 假设数据库中的时间是UTC无时区信息，这里手动视为UTC再加8小时
        aware = self.created_at.replace(tzinfo=timezone.utc)
        return aware + timedelta(hours=8)

    def __repr__(self):
        return f'<Comment {self.id}>'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))