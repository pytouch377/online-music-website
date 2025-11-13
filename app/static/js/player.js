class MusicPlayer {
    constructor() {
        this.audio = document.getElementById('main-audio');
        this.player = document.getElementById('audio-player');
        this.currentSong = null;
        this.isPlaying = false;
        this.labels = window.APP_I18N || {};
        
        this.initializeEventListeners();
        this.setupAudioEvents();
    }
    
    t(key, fallback = '') {
        return this.labels[key] || fallback;
    }

    format(key, fallback = '', params = {}) {
        let message = this.t(key, fallback);
        Object.entries(params).forEach(([paramKey, value]) => {
            message = message.replace(`%(${paramKey})s`, value);
        });
        return message;
    }
    
    initializeEventListeners() {
        // 使用事件委托来处理播放/暂停按钮
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('play-btn')) {
                const songId = e.target.getAttribute('data-song-id');
                this.handlePlayPauseClick(songId);
            }
        });
    }
    
    handlePlayPauseClick(songId) {
        // 如果是当前正在播放的歌曲
        if (this.currentSong && this.currentSong.id == songId) {
            if (this.isPlaying) {
                // 正在播放 → 暂停
                this.pause();
            } else {
                // 已暂停 → 继续播放
                this.resume();
            }
        } else {
            // 其他歌曲 → 播放新歌曲
            this.playSong(songId);
        }
    }
    
    setupAudioEvents() {
        this.audio.addEventListener('play', () => {
            this.isPlaying = true;
            this.updatePlayButtonStates();
            this.showPlayer();
        });
        
        this.audio.addEventListener('pause', () => {
            this.isPlaying = false;
            this.updatePlayButtonStates();
        });
        
        this.audio.addEventListener('ended', () => {
            this.isPlaying = false;
            this.updatePlayButtonStates();
        });
        
        this.audio.addEventListener('error', (e) => {
            console.error('🎵 Audio error:', e);
            this.showError(this.t('audio_error', 'Audio playback error. Please check the file format.'));
        });
    }
    
    async playSong(songId) {
        try {
            console.log(`🎵 Attempting to play song ID: ${songId}`);
            
            const response = await fetch(`/api/song/${songId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const song = await response.json();
            console.log('🎵 Song data received:', song);
            
            this.currentSong = song;
            
            // 设置音频源（如果是新歌曲）
            if (this.audio.src !== song.file_path) {
                this.audio.src = song.file_path;
                console.log('🎵 Audio source set to:', song.file_path);
            }
            
            // 显示播放器
            this.showPlayer();
            
            // 显示当前播放信息
            this.showNowPlaying(song);
            
            // 开始播放
            await this.startPlayback();
            
        } catch (error) {
            console.error('🎵 Error playing song:', error);
            this.showError(this.format('error_playing_song', 'Error playing song: %(error)s', { error: error.message }));
        }
    }
    
    async startPlayback() {
        try {
            console.log('🎵 Starting playback...');
            const playPromise = this.audio.play();
            
            if (playPromise !== undefined) {
                await playPromise;
                console.log('🎵 Playback started successfully');
                this.isPlaying = true;
                this.updatePlayButtonStates();
            }
        } catch (error) {
            console.error('🎵 Playback failed:', error);
            this.showError(this.format('unable_to_play', 'Unable to play audio: %(error)s', { error: error.message }));
            throw error;
        }
    }
    
    pause() {
        if (this.isPlaying) {
            console.log('🎵 Pausing playback');
            this.audio.pause();
            this.isPlaying = false;
            this.updatePlayButtonStates();
        }
    }
    
    resume() {
        if (!this.isPlaying && this.currentSong) {
            console.log('🎵 Resuming playback');
            this.startPlayback().catch(error => {
                console.error('🎵 Resume failed:', error);
            });
        }
    }
    
    stop() {
        console.log('🎵 Stopping playback');
        this.audio.pause();
        this.audio.currentTime = 0;
        this.isPlaying = false;
        this.updatePlayButtonStates();
    }
    
    showPlayer() {
        this.player.style.display = 'block';
        // 平滑滚动到播放器
        setTimeout(() => {
            this.player.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }
    
    updatePlayButtonStates() {
        const playButtons = document.querySelectorAll('.play-btn');
        playButtons.forEach(btn => {
            const songId = btn.getAttribute('data-song-id');
            
            // 如果是当前播放的歌曲
            if (this.currentSong && songId === this.currentSong.id.toString()) {
                if (this.isPlaying) {
                    // 正在播放：显示暂停按钮
                    btn.innerHTML = this.t('pause_label', '⏸️ Pause');
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-warning');
                } else {
                    // 已暂停：显示播放按钮（继续播放）
                    btn.innerHTML = this.t('play_label', '▶️ Play');
                    btn.classList.remove('btn-warning');
                    btn.classList.add('btn-primary');
                }
            } else {
                // 其他歌曲：显示普通播放按钮
                btn.innerHTML = this.t('play_label', '▶️ Play');
                btn.classList.remove('btn-warning');
                btn.classList.add('btn-primary');
            }
        });
    }
    
    showNowPlaying(song) {
        let nowPlayingDiv = this.player.querySelector('.now-playing-info');
        if (!nowPlayingDiv) {
            nowPlayingDiv = document.createElement('div');
            nowPlayingDiv.className = 'now-playing-info mb-2 p-2 bg-light rounded';
            this.audio.parentNode.insertBefore(nowPlayingDiv, this.audio);
        }
        
        const status = this.isPlaying ? '▶️' : '⏸️';
        nowPlayingDiv.innerHTML = `
            <strong>${status} ${this.t('now_playing', 'Now Playing:')}</strong> ${song.title} - ${song.artist}
            ${song.album ? `<br><small>💿 ${this.t('album_label', 'Album:')} ${song.album}</small>` : ''}
        `;
    }
    
    showError(message) {
        // 使用Toast通知
        this.showToast(message, 'danger');
    }
    
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0`;
        toast.id = toastId;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }
}

// 初始化播放器
document.addEventListener('DOMContentLoaded', () => {
    window.musicPlayer = new MusicPlayer();
    console.log('🎵 Music player initialized');
});