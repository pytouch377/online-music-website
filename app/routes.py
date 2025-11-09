import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app import db
from app.models import Song, Playlist, PlaylistItem, Favorite, User, Comment
from app.forms import SongUploadForm, PlaylistForm
import uuid
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

# 首页路由定义在文件下方（避免重复定义）

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
            audio_db_path = os.path.join('uploads', 'audio', unique_audio_filename).replace('\\', '/')
            
            # 处理封面图片上传（如果有）
            cover_db_path = None
            if form.cover_image.data and form.cover_image.data.filename:
                cover_file = form.cover_image.data
                if allowed_file(cover_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                    cover_filename = secure_filename(cover_file.filename)
                    unique_cover_filename = get_unique_filename(cover_filename)
                    cover_save_path = os.path.join(cover_upload_dir, unique_cover_filename)
                    cover_file.save(cover_save_path)
                    cover_db_path = os.path.join('uploads', 'covers', unique_cover_filename).replace('\\', '/')
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
                user_id=current_user.id,
                visibility=form.visibility.data  # 确保这行存在
            )
            
            db.session.add(song)
            db.session.commit()

            visibility_msg = "publicly shared" if form.visibility.data == 'public' else "privately saved"

            flash(f'🎵 Your song has been uploaded successfully and is {visibility_msg}!', 'success')
            return redirect(url_for('main.library'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading file: {str(e)}', 'error')
            print(f"Upload error: {e}")  # 用于调试
    
    return render_template('upload.html', title='Upload Song', form=form)

@bp.route('/library')
def library():
    page = request.args.get('page', 1, type=int)
    # 只显示公开的音乐
    songs = Song.query.filter_by(visibility='public').order_by(Song.upload_date.desc()).paginate(
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
        # 只在公开音乐中搜索
        songs = Song.query.filter(
            Song.visibility == 'public',
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



# 首页 - 显示公共内容和个人推荐
@bp.route('/')
def index():
    # 公共热门歌曲
    public_songs = Song.query.filter_by(visibility='public').order_by(Song.play_count.desc()).limit(6).all()
    
    # 新上传的公共歌曲
    new_songs = Song.query.filter_by(visibility='public').order_by(Song.upload_date.desc()).limit(6).all()
    
    return render_template('index.html', title='Home', 
                         public_songs=public_songs, new_songs=new_songs)

# 个人收藏
@bp.route('/favorites')
@login_required
def favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    favorite_songs = [fav.song for fav in favorites]
    return render_template('favorites.html', title='My Favorites', songs=favorite_songs)

# 添加/取消收藏
@bp.route('/favorite/<int:song_id>', methods=['POST'])
@login_required
def favorite_song(song_id):
    song = Song.query.get_or_404(song_id)
    favorite = Favorite.query.filter_by(user_id=current_user.id, song_id=song_id).first()
    
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'status': 'removed', 'message': 'Removed from favorites'})
    else:
        favorite = Favorite(user_id=current_user.id, song_id=song_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'status': 'added', 'message': 'Added to favorites'})

# 用户个人主页
@bp.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    public_songs = Song.query.filter_by(user_id=user.id, visibility='public').all()
    public_playlists = Playlist.query.filter_by(user_id=user.id, visibility='public').all()
    
    return render_template('user_profile.html', title=f"{username}'s Profile", 
                         user=user, songs=public_songs, playlists=public_playlists)

@bp.route('/my_music')
@login_required
def my_music():
    """显示用户的所有音乐（公开和私人）"""
    page = request.args.get('page', 1, type=int)
    songs = Song.query.filter_by(user_id=current_user.id).order_by(Song.upload_date.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('my_music.html', title='My Music', songs=songs)

# API端点 - 获取歌曲信息
@bp.route('/api/song/<int:song_id>')
def get_song(song_id):
    song = Song.query.get_or_404(song_id)

    # 调试信息：检查文件是否存在
    file_full_path = os.path.join(current_app.root_path, 'static', song.file_path)
    file_exists = os.path.exists(file_full_path)
    
    print(f"🎵 Song: {song.title}")
    print(f"📁 File path in DB: {song.file_path}")
    print(f"📁 Full path: {file_full_path}")
    print(f"✅ File exists: {file_exists}")

    return jsonify({
        'id': song.id,
        'title': song.title,
        'artist': song.artist,
        'album': song.album,
        'file_path': url_for('static', filename=song.file_path),
        'cover_image': url_for('static', filename=song.cover_image) if song.cover_image else None
    })

@bp.route('/test_audio')
def test_audio():
    """测试音频播放的专用页面"""
    # 使用多个不同的音频源进行测试
    test_audios = [
        {
            'name': 'Tech House Vibes',
            'url': 'https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3',
            'type': 'mp3'
        },
        {
            'name': 'Simple Piano',
            'url': 'https://assets.mixkit.co/music/preview/mixkit-simple-piano-melody-983.mp3', 
            'type': 'mp3'
        }
    ]
    
    return render_template('test_audio.html', title='Audio Test', test_audios=test_audios)

@bp.route('/api/test_audio/<int:index>')
def api_test_audio(index):
    """测试音频API端点"""
    test_audios = [
        'https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3',
        'https://assets.mixkit.co/music/preview/mixkit-simple-piano-melody-983.mp3'
    ]
    
    if 0 <= index < len(test_audios):
        return jsonify({
            'file_path': test_audios[index],
            'title': f'Test Audio {index + 1}',
            'artist': 'Test Artist',
            'album': 'Test Album'
        })
    else:
        return jsonify({'error': 'Invalid audio index'}), 404