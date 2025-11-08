import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app import db
from app.models import Song, Playlist, PlaylistItem
from app.forms import SongUploadForm, PlaylistForm
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

bp = Blueprint('main', __name__)

# 允许的文件扩展名
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_unique_filename(filename):
    """生成唯一文件名防止冲突"""
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    return unique_filename

@bp.route('/')
def index():
    songs = Song.query.order_by(Song.upload_date.desc()).limit(10).all()
    return render_template('index.html', title='Home', songs=songs)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = SongUploadForm()
    if form.validate_on_submit():
        # 检查音频文件
        audio_file = form.audio_file.data
        if not audio_file or not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            flash('Please select a valid audio file (MP3, WAV, OGG, FLAC, M4A).', 'error')
            return render_template('upload.html', title='Upload Song', form=form)
        
        try:
            # 创建上传目录 - 使用绝对路径
            upload_base = os.path.join(current_app.root_path, 'static', 'uploads')
            audio_upload_dir = os.path.join(upload_base, 'audio')
            cover_upload_dir = os.path.join(upload_base, 'covers')
            
            os.makedirs(audio_upload_dir, exist_ok=True)
            os.makedirs(cover_upload_dir, exist_ok=True)
            
            # 处理音频文件上传
            audio_filename = secure_filename(audio_file.filename)
            unique_audio_filename = get_unique_filename(audio_filename)
            audio_save_path = os.path.join(audio_upload_dir, unique_audio_filename)
            audio_file.save(audio_save_path)
            
            # 数据库中的相对路径
            audio_db_path = os.path.join('uploads', 'audio', unique_audio_filename)
            
            # 处理封面图片上传（如果有）
            cover_db_path = None
            if form.cover_image.data and form.cover_image.data.filename:
                cover_file = form.cover_image.data
                if allowed_file(cover_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                    cover_filename = secure_filename(cover_file.filename)
                    unique_cover_filename = get_unique_filename(cover_filename)
                    cover_save_path = os.path.join(cover_upload_dir, unique_cover_filename)
                    cover_file.save(cover_save_path)
                    cover_db_path = os.path.join('uploads', 'covers', unique_cover_filename)
                else:
                    flash('Invalid image file type. Please use JPG, PNG, or GIF.', 'warning')
            
            # 创建歌曲记录
            song = Song(
                title=form.title.data,
                artist=form.artist.data,
                album=form.album.data or '',
                genre=form.genre.data or '',
                file_path=audio_db_path,
                cover_image=cover_db_path,
                user_id=current_user.id
            )
            
            db.session.add(song)
            db.session.commit()
            flash('🎵 Your song has been uploaded successfully!', 'success')
            return redirect(url_for('main.library'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading file: {str(e)}', 'error')
            print(f"Upload error: {e}")  # 用于调试
    
    return render_template('upload.html', title='Upload Song', form=form)

@bp.route('/library')
def library():
    page = request.args.get('page', 1, type=int)
    songs = Song.query.order_by(Song.upload_date.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('library.html', title='Music Library', songs=songs)

@bp.route('/playlists')
@login_required
def playlists():
    playlists = current_user.playlists.all()
    return render_template('playlists.html', title='My Playlists', playlists=playlists)

@bp.route('/create_playlist', methods=['GET', 'POST'])
@login_required
def create_playlist():
    form = PlaylistForm()
    if form.validate_on_submit():
        playlist = Playlist(
            name=form.name.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(playlist)
        db.session.commit()
        flash('Your playlist has been created!')
        return redirect(url_for('main.playlists'))
    
    return render_template('create_playlist.html', title='Create Playlist', form=form)

@bp.route('/playlist/<int:playlist_id>')
def playlist_detail(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    return render_template('playlist_detail.html', title=playlist.name, playlist=playlist)

@bp.route('/add_to_playlist/<int:song_id>', methods=['POST'])
@login_required
def add_to_playlist(song_id):
    playlist_id = request.form.get('playlist_id')
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # 检查用户是否拥有该播放列表
    if playlist.user_id != current_user.id:
        flash('You can only add songs to your own playlists.')
        return redirect(url_for('main.library'))
    
    # 检查歌曲是否已在播放列表中
    existing_item = PlaylistItem.query.filter_by(
        playlist_id=playlist_id, song_id=song_id).first()
    if existing_item:
        flash('This song is already in the playlist.')
        return redirect(url_for('main.library'))
    
    # 获取当前播放列表中的最大顺序值
    max_order = db.session.query(db.func.max(PlaylistItem.order)).filter_by(
        playlist_id=playlist_id).scalar() or 0
    
    playlist_item = PlaylistItem(
        playlist_id=playlist_id,
        song_id=song_id,
        order=max_order + 1
    )
    
    db.session.add(playlist_item)
    db.session.commit()
    flash('Song added to playlist!')
    return redirect(url_for('main.library'))

@bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    if query:
        # 实现真正的搜索功能
        songs = Song.query.filter(
            (Song.title.ilike(f'%{query}%')) | 
            (Song.artist.ilike(f'%{query}%')) |
            (Song.album.ilike(f'%{query}%')) |
            (Song.genre.ilike(f'%{query}%'))
        ).order_by(Song.title).paginate(
            page=page, per_page=12, error_out=False)
    else:
        # 如果没有搜索词，显示空结果
        songs = []
    
    return render_template('search.html', title='Search', songs=songs, query=query)

# API端点 - 获取歌曲信息
@bp.route('/api/song/<int:song_id>')
def get_song(song_id):
    song = Song.query.get_or_404(song_id)
    return jsonify({
        'id': song.id,
        'title': song.title,
        'artist': song.artist,
        'album': song.album,
        'file_path': url_for('static', filename=song.file_path),
        'cover_image': url_for('static', filename=song.cover_image) if song.cover_image else None
    })