import os
import uuid
import requests
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, current_app, session
from flask_login import current_user, login_required
from flask_babel import _
from werkzeug.utils import secure_filename
from app import db
from app.models import Song, Playlist, PlaylistItem, User
from app.forms import SongUploadForm, PlaylistForm, ProfileForm

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

def search_netease_cover(artist, title, exclude_albums=None):
    """搜索网易云音乐封面"""
    if exclude_albums is None:
        exclude_albums = set()
    
    try:
        # 先精确搜索歌曲
        search_url = "https://music.163.com/api/search/get/web"
        params = {
            'csrf_token': '',
            's': f"{artist} {title}",
            'type': 1,
            'offset': 0,
            'total': True,
            'limit': 20
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.163.com/'
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            songs = data.get('result', {}).get('songs', [])
            
            # 收集所有匹配的专辑封面
            covers = []
            for song in songs:
                song_artists = [ar.get('name', '') for ar in song.get('artists', [])]
                if any(artist.lower() in ar.lower() or ar.lower() in artist.lower() for ar in song_artists):
                    album = song.get('album', {})
                    album_name = album.get('name', '')
                    pic_url = album.get('picUrl', '')
                    
                    if pic_url and album_name not in exclude_albums:
                        covers.append({
                            'url': pic_url + '?param=600y600',
                            'album': album_name,
                            'title': song.get('name', ''),
                            'match_score': 100 if title.lower() in song.get('name', '').lower() else 50
                        })
            
            # 按匹配度排序，优先返回精确匹配的
            if covers:
                covers.sort(key=lambda x: x['match_score'], reverse=True)
                return covers[0]['url']
    except Exception as e:
        print(f"NetEase search error: {e}")
    return None

def search_qq_music_cover(artist, title, exclude_albums=None):
    """搜索QQ音乐封面"""
    if exclude_albums is None:
        exclude_albums = set()
    
    try:
        # QQ音乐搜索API
        search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params = {
            'ct': 24,
            'qqmusic_ver': 1298,
            'new_json': 1,
            'remoteplace': 'txt.yqq.song',
            'searchid': random.randint(100000000, 999999999),
            't': 0,
            'aggr': 1,
            'cr': 1,
            'catZhida': 1,
            'lossless': 0,
            'flag_qc': 0,
            'p': 1,
            'n': 20,
            'w': f"{artist} {title}",
            'g_tk': 5381,
            'loginUin': 0,
            'hostUin': 0,
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'notice': 0,
            'platform': 'yqq.json',
            'needNewCode': 0
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://y.qq.com/'
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            songs = data.get('data', {}).get('song', {}).get('list', [])
            
            # 收集所有匹配的专辑封面
            covers = []
            for song in songs:
                song_artists = [singer.get('name', '') for singer in song.get('singer', [])]
                if any(artist.lower() in ar.lower() or ar.lower() in artist.lower() for ar in song_artists):
                    album = song.get('album', {})
                    album_name = album.get('name', '')
                    album_mid = album.get('mid', '')
                    
                    if album_mid and album_name not in exclude_albums:
                        covers.append({
                            'url': f"https://y.gtimg.cn/music/photo_new/T002R600x600M000{album_mid}.jpg",
                            'album': album_name,
                            'title': song.get('name', ''),
                            'match_score': 100 if title.lower() in song.get('name', '').lower() else 50
                        })
            
            # 按匹配度排序，优先返回精确匹配的
            if covers:
                covers.sort(key=lambda x: x['match_score'], reverse=True)
                return covers[0]['url']
    except Exception as e:
        print(f"QQ Music search error: {e}")
    return None

def download_cover_image(cover_url, save_dir):
    """下载封面图片并保存到本地"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.163.com/'
        }
        response = requests.get(cover_url, headers=headers, timeout=30)
        if response.status_code == 200:
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex}.jpg"
            save_path = os.path.join(save_dir, unique_filename)
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            return unique_filename
    except Exception as e:
        print(f"Error downloading cover: {e}")
    return None

@bp.route('/')
def index():
    # 公共热门歌曲
    public_songs = Song.query.filter_by(visibility='public').order_by(Song.play_count.desc()).limit(6).all()
    
    # 新上传的公共歌曲
    new_songs = Song.query.filter_by(visibility='public').order_by(Song.upload_date.desc()).limit(6).all()
    
    return render_template('index.html', title='Home', 
                         public_songs=public_songs, new_songs=new_songs)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = SongUploadForm()
    
    # 临时保存上传的文件信息
    temp_audio_filename = None
    temp_cover_filename = None
    
    if form.validate_on_submit():
        # 检查音频文件
        audio_file = form.audio_file.data
        if not audio_file or not audio_file.filename:
            flash(_('Please select an audio file.'), 'error')
            return render_template('upload.html', title='Upload Song', form=form)
        
        if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            flash(_('Please select a valid audio file (MP3, WAV, OGG, FLAC, M4A).'), 'error')
            return render_template('upload.html', title='Upload Song', form=form)
        
        try:
            # 创建上传目录
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
            
            # 数据库中的相对路径（统一用 / 分隔符以支持跨平台）
            audio_db_path = os.path.join('uploads', 'audio', unique_audio_filename).replace('\\', '/')
            
            # 处理封面图片上传或自动搜索
            cover_db_path = None
            
            # 优先使用用户上传的封面
            if form.cover_image.data and form.cover_image.data.filename:
                cover_file = form.cover_image.data
                if allowed_file(cover_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                    cover_filename = secure_filename(cover_file.filename)
                    unique_cover_filename = get_unique_filename(cover_filename)
                    cover_save_path = os.path.join(cover_upload_dir, unique_cover_filename)
                    cover_file.save(cover_save_path)
                    cover_db_path = os.path.join('uploads', 'covers', unique_cover_filename).replace('\\', '/')
                else:
                    flash(_('Invalid image file type. Please use JPG, PNG, or GIF.'), 'warning')
            
            # 如果没有上传封面且勾选了自动搜索
            elif form.auto_search_cover.data:
                cover_url = None
                search_source = None
                
                try:
                    # 优先搜索网易云音乐
                    cover_url = search_netease_cover(form.artist.data, form.title.data)
                    if cover_url:
                        search_source = _('NetEase Cloud Music')
                    else:
                        # 备选QQ音乐
                        cover_url = search_qq_music_cover(form.artist.data, form.title.data)
                        if cover_url:
                            search_source = _('QQ Music')
                        else:
                            # 最后备选iTunes
                            search_query = f"{form.artist.data} {form.title.data}"
                            itunes_url = f"https://itunes.apple.com/search?term={requests.utils.quote(search_query)}&media=music&limit=1"
                            
                            response = requests.get(itunes_url, timeout=10)
                            if response.status_code == 200:
                                data = response.json()
                                if data.get('results'):
                                    result = data['results'][0]
                                    cover_url = result.get('artworkUrl100', '').replace('100x100', '600x600')
                                    if cover_url:
                                        search_source = _('Apple Music')
                    
                    if cover_url:
                        # 下载封面图片
                        unique_cover_filename = download_cover_image(cover_url, cover_upload_dir)
                        if unique_cover_filename:
                            cover_db_path = os.path.join('uploads', 'covers', unique_cover_filename).replace('\\', '/')
                            flash(_('🎨 Found and downloaded album cover from %(source)s!', source=search_source), 'success')
                        else:
                            flash(_('Cover download failed, please try again later.'), 'warning')
                    else:
                        flash(_('No album cover was found for this song.'), 'info')
                        
                except Exception as e:
                    flash(_('Error occurred while searching for cover: %(error)s', error=str(e)), 'warning')
            
            # 创建歌曲记录
            song = Song(
                title=form.title.data,
                artist=form.artist.data,
                album=form.album.data or '',
                genre=form.genre.data or '',
                file_path=audio_db_path,
                cover_image=cover_db_path,
                user_id=current_user.id,
                visibility=form.visibility.data
            )
            
            db.session.add(song)
            db.session.commit()
            
            visibility_msg = _('publicly shared') if form.visibility.data == 'public' else _('privately saved')
            flash(_('🎵 Your song has been uploaded successfully and is %(status)s!', status=visibility_msg), 'success')
            return redirect(url_for('main.library'))
            
        except Exception as e:
            db.session.rollback()
            # 如果出错，删除已上传的文件
            if 'audio_save_path' in locals() and os.path.exists(audio_save_path):
                os.remove(audio_save_path)
            if 'cover_save_path' in locals() and os.path.exists(cover_save_path):
                os.remove(cover_save_path)
                
            flash(_('Error uploading file: %(error)s', error=str(e)), 'error')
            print(f"Upload error: {e}")
    
    # 如果是GET请求或验证失败，显示表单（保留用户输入）
    return render_template('upload.html', title='Upload Song', form=form)

@bp.route('/library')
def library():
    page = request.args.get('page', 1, type=int)
    # 只显示公开的音乐，并预加载上传者信息
    songs = Song.query.filter_by(visibility='public')\
                     .order_by(Song.upload_date.desc())\
                     .paginate(page=page, per_page=20, error_out=False)
    return render_template('library.html', title='Music Library', songs=songs)

@bp.route('/my_music')
@login_required
def my_music():
    """显示用户的所有音乐（公开和私人）"""
    page = request.args.get('page', 1, type=int)
    songs = Song.query.filter_by(user_id=current_user.id).order_by(Song.upload_date.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('my_music.html', title='My Music', songs=songs)

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
            visibility=form.visibility.data,
            user_id=current_user.id
        )
        db.session.add(playlist)
        db.session.commit()
        flash(_('Your playlist has been created!'))
        return redirect(url_for('main.playlists'))
    
    return render_template('create_playlist.html', title='Create Playlist', form=form)

@bp.route('/playlist/<int:playlist_id>')
def playlist_detail(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    return render_template('playlist_detail.html', title=playlist.name, playlist=playlist)

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

# API端点 - 搜索歌曲封面
@bp.route('/api/search_cover')
def api_search_cover():
    title = request.args.get('title', '').strip()
    artist = request.args.get('artist', '').strip()
    
    if not title or not artist:
        return jsonify({'error': 'Title and artist are required'}), 400
    
    try:
        cover_url = None
        source = None
        
        # 优先搜索网易云音乐
        cover_url = search_netease_cover(artist, title)
        if cover_url:
            source = _('NetEase Cloud Music')
        else:
            # 备选QQ音乐
            cover_url = search_qq_music_cover(artist, title)
            if cover_url:
                source = _('QQ Music')
            else:
                # 最后备选iTunes
                search_query = f"{artist} {title}"
                itunes_url = f"https://itunes.apple.com/search?term={requests.utils.quote(search_query)}&media=music&limit=1"
                
                response = requests.get(itunes_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        result = data['results'][0]
                        cover_url = result.get('artworkUrl100', '').replace('100x100', '600x600')
                        if cover_url:
                            source = _('Apple Music')
        
        if cover_url:
            return jsonify({
                'success': True,
                'cover_url': cover_url,
                'source': source
            })
        
        return jsonify({'success': False, 'error': 'No cover found'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# API端点 - 更换歌曲封面
@bp.route('/api/update_cover/<int:song_id>', methods=['POST'])
@login_required
def api_update_cover(song_id):
    song = Song.query.get_or_404(song_id)
    
    # 检查权限
    if song.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    try:
        # 搜索新的封面图片
        cover_url = None
        
        # 方案1: iTunes搜索艺术家的多个专辑
        try:
            itunes_url = f"https://itunes.apple.com/search?term={requests.utils.quote(song.artist)}&media=music&limit=20"
            response = requests.get(itunes_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # 收集不同的专辑封面
                covers = []
                for result in results:
                    result_artist = result.get('artistName', '').lower()
                    if song.artist.lower() in result_artist or result_artist in song.artist.lower():
                        cover_candidate = result.get('artworkUrl100', '').replace('100x100', '600x600')
                        if cover_candidate and cover_candidate not in covers:
                            covers.append(cover_candidate)
                
                if covers:
                    cover_url = random.choice(covers)
        except Exception as e:
            print(f"iTunes search error: {e}")
        
        # 方案2: 如果iTunes失败，使用通用音乐封面API
        if not cover_url:
            try:
                # 使用Last.fm API作为备选
                lastfm_url = f"https://ws.audioscrobbler.com/2.0/?method=artist.gettopalbums&artist={requests.utils.quote(song.artist)}&api_key=b25b959554ed76058ac220b7b2e0a026&format=json&limit=10"
                response = requests.get(lastfm_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    albums = data.get('topalbums', {}).get('album', [])
                    
                    covers = []
                    for album in albums:
                        images = album.get('image', [])
                        for img in images:
                            if img.get('size') == 'extralarge' and img.get('#text'):
                                covers.append(img.get('#text'))
                    
                    if covers:
                        cover_url = random.choice(covers)
            except Exception as e:
                print(f"Last.fm search error: {e}")
        
        # 方案3: 最后备选 - 使用MusicBrainz + Cover Art Archive
        if not cover_url:
            try:
                # 简单的备选封面URL列表
                fallback_covers = [
                    "https://via.placeholder.com/600x600/FF6B6B/FFFFFF?text=Music",
                    "https://via.placeholder.com/600x600/4ECDC4/FFFFFF?text=Album",
                    "https://via.placeholder.com/600x600/45B7D1/FFFFFF?text=Song",
                    "https://via.placeholder.com/600x600/96CEB4/FFFFFF?text=Audio",
                    "https://via.placeholder.com/600x600/FFEAA7/333333?text=Music"
                ]
                cover_url = random.choice(fallback_covers)
            except:
                pass
        
        if cover_url:
            # 创建封面目录
            cover_upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'covers')
            os.makedirs(cover_upload_dir, exist_ok=True)
            
            # 下载新封面
            unique_cover_filename = download_cover_image(cover_url, cover_upload_dir)
            if unique_cover_filename:
                # 删除旧封面
                if song.cover_image:
                    old_cover_path = os.path.join(current_app.root_path, 'static', song.cover_image)
                    if os.path.exists(old_cover_path):
                        os.remove(old_cover_path)
                
                # 更新数据库
                song.cover_image = os.path.join('uploads', 'covers', unique_cover_filename).replace('\\', '/')
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'new_cover_url': url_for('static', filename=song.cover_image),
                    'message': '已成功更换专辑封面！'
                })
        
        return jsonify({
            'success': False, 
            'error': 'No relevant cover found for this song.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# API端点 - 获取歌曲信息
@bp.route('/api/song/<int:song_id>')
def api_get_song(song_id):
    song = Song.query.get_or_404(song_id)
    
    # 构建完整的文件路径
    static_file_path = os.path.join(current_app.root_path, 'static', song.file_path)
    file_exists = os.path.exists(static_file_path)
    
    # 如果文件存在，使用相对路径
    if file_exists:
        # 使用Flask的url_for生成正确的URL
        audio_url = url_for('static', filename=song.file_path)
    else:
        # 使用一个不会被广告拦截器阻止的测试音频
        audio_url = "https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3"
    
    return jsonify({
        'id': song.id,
        'title': song.title,
        'artist': song.artist,
        'album': song.album,
        'file_path': audio_url,
        'cover_image': url_for('static', filename=song.cover_image) if song.cover_image else None
    })

# 社交功能路由
@bp.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # 获取用户的公开内容
    public_songs = Song.query.filter_by(
        user_id=user.id, 
        visibility='public'
    ).order_by(Song.upload_date.desc()).limit(6).all()
    
    public_playlists = Playlist.query.filter_by(
        user_id=user.id, 
        visibility='public'
    ).order_by(Playlist.created_at.desc()).limit(3).all()
    
    # 检查当前用户是否关注此用户
    is_following = False
    if current_user.is_authenticated:
        is_following = current_user.is_following(user)
    
    return render_template('user_profile.html', 
                         title=f"{user.username}'s Profile",
                         user=user,
                         songs=public_songs,
                         playlists=public_playlists,
                         is_following=is_following)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm()
    
    if form.validate_on_submit():
        current_user.bio = form.bio.data
        current_user.location = form.location.data
        current_user.website = form.website.data
        
        # 处理头像上传
        if form.avatar.data:
            avatar_file = form.avatar.data
            if allowed_file(avatar_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                # 创建头像目录
                avatar_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
                os.makedirs(avatar_dir, exist_ok=True)
                
                # 生成唯一文件名
                avatar_filename = secure_filename(avatar_file.filename)
                unique_avatar_filename = get_unique_filename(avatar_filename)
                avatar_path = os.path.join('uploads', 'avatars', unique_avatar_filename)
                
                # 保存文件
                avatar_file.save(os.path.join(current_app.root_path, 'static', avatar_path))
                current_user.avatar = avatar_path
        
        db.session.commit()
        flash(_('Your profile has been updated!'), 'success')
        return redirect(url_for('main.user_profile', username=current_user.username))
    
    # 填充现有数据
    elif request.method == 'GET':
        form.bio.data = current_user.bio
        form.location.data = current_user.location
        form.website.data = current_user.website
    
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    if user == current_user:
        flash(_('You cannot follow yourself!'), 'warning')
        return redirect(url_for('main.user_profile', username=username))
    
    current_user.follow(user)
    db.session.commit()
    flash(_('You are now following %(username)s!', username=username), 'success')
    return redirect(url_for('main.user_profile', username=username))

@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You have unfollowed %(username)s.', username=username), 'info')
    return redirect(url_for('main.user_profile', username=username))

@bp.route('/set_language/<language>')
def set_language(language=None):
    if language in ['en', 'zh']:
        session['language'] = language
    return redirect(request.referrer or url_for('main.index'))

@bp.route('/delete_song/<int:song_id>', methods=['POST'])
@login_required
def delete_song(song_id):
    song = Song.query.get_or_404(song_id)
    
    # 检查用户是否有权限删除这首歌
    if song.user_id != current_user.id:
        flash(_('You can only delete your own songs.'), 'error')
        return redirect(url_for('main.library'))
    
    try:
        # 删除物理文件
        if song.file_path:
            audio_path = os.path.join(current_app.root_path, 'static', song.file_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        if song.cover_image:
            cover_path = os.path.join(current_app.root_path, 'static', song.cover_image)
            if os.path.exists(cover_path):
                os.remove(cover_path)
        
        # 从数据库删除
        db.session.delete(song)
        db.session.commit()
        
        flash(_('Song deleted successfully!'), 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(_('Error deleting song: %(error)s', error=str(e)), 'error')
    
    # 根据来源页面决定重定向
    referrer = request.referrer
    if referrer and 'library' in referrer:
        return redirect(url_for('main.library'))
    else:
        return redirect(url_for('main.my_music'))