from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    playlists = db.relationship('Playlist', backref='creator', lazy='dynamic')
    uploaded_songs = db.relationship('Song', backref='uploader', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
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
    
    # 关系
    playlist_items = db.relationship('PlaylistItem', backref='song', lazy='dynamic')
    
    def __repr__(self):
        return f'<Song {self.title} by {self.artist}>'

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
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

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))