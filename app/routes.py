import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app import db
from app.models import Song, Playlist, PlaylistItem
from app.forms import SongUploadForm, PlaylistForm

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    songs = Song.query.order_by(Song.upload_date.desc()).limit(10).all()
    return render_template('index.html', title='Home', songs=songs)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = SongUploadForm()
    if form.validate_on_submit():
        # 处理音频文件上传
        audio_file = form.audio_file.data
        audio_filename = secure_filename(audio_file.filename)
        audio_path = os.path.join('uploads', 'audio', audio_filename)
        audio_file.save(os.path.join('app/static', audio_path))
        
        # 处理封面图片上传（如果有）
        cover_path = None
        if form.cover_image.data:
            cover_file = form.cover_image.data
            cover_filename = secure_filename(cover_file.filename)
            cover_path = os.path.join('uploads', 'covers', cover_filename)
            cover_file.save(os.path.join('app/static', cover_path))
        
        song = Song(
            title=form.title.data,
            artist=form.artist.data,
            album=form.album.data,
            genre=form.genre.data,
            file_path=audio_path,
            cover_image=cover_path,
            user_id=current_user.id
        )
        
        db.session.add(song)
        db.session.commit()
        flash('Your song has been uploaded!')
        return redirect(url_for('main.index'))
    
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
    query = request.args.get('q', '')
    if query:
        songs = Song.query.filter(
            (Song.title.ilike(f'%{query}%')) | 
            (Song.artist.ilike(f'%{query}%')) |
            (Song.album.ilike(f'%{query}%'))
        ).all()
    else:
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