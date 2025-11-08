class MusicPlayer {
    constructor() {
        this.audio = document.getElementById('main-audio');
        this.player = document.getElementById('audio-player');
        this.currentSong = null;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // 播放按钮点击事件
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('play-btn')) {
                const songId = e.target.getAttribute('data-song-id');
                this.playSong(songId);
            }
        });
        
        // 添加到播放列表模态框
        const addToPlaylistModal = document.getElementById('addToPlaylistModal');
        if (addToPlaylistModal) {
            addToPlaylistModal.addEventListener('show.bs.modal', (event) => {
                const button = event.relatedTarget;
                const songId = button.getAttribute('data-song-id');
                document.getElementById('modalSongId').value = songId;
            });
        }
        
        // 添加到播放列表表单提交
        const addToPlaylistForm = document.getElementById('addToPlaylistForm');
        if (addToPlaylistForm) {
            addToPlaylistForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addToPlaylist();
            });
        }
    }
    
    async playSong(songId) {
        try {
            const response = await fetch(`/api/song/${songId}`);
            const song = await response.json();
            
            this.currentSong = song;
            this.audio.src = song.file_path;
            this.player.style.display = 'block';
            this.audio.play();
            
            // 更新播放器界面（可选）
            this.updatePlayerUI(song);
        } catch (error) {
            console.error('Error playing song:', error);
        }
    }
    
    updatePlayerUI(song) {
        // 这里可以添加更新播放器UI的代码
        console.log('Now playing:', song.title);
    }
    
    async addToPlaylist() {
        const formData = new FormData(document.getElementById('addToPlaylistForm'));
        
        try {
            const response = await fetch('/add_to_playlist/' + formData.get('song_id'), {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('addToPlaylistModal'));
                modal.hide();
                
                // 显示成功消息或刷新页面
                window.location.reload();
            }
        } catch (error) {
            console.error('Error adding to playlist:', error);
        }
    }
}

// 初始化播放器
document.addEventListener('DOMContentLoaded', () => {
    new MusicPlayer();
});