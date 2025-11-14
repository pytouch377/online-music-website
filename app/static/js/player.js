// 全局变量
let currentPlayButton = null;
let allPlayButtons = {};

// 播放音频函数
function playAudio(songId) {
    const audioPlayer = document.getElementById('main-audio');
    const playerContainer = document.getElementById('audio-player');
    const playButton = document.querySelector(`[data-song-id="${songId}"]`) || document.getElementById(`play-btn-${songId}`);
    
    // 保存按钮引用
    if (playButton) {
        allPlayButtons[songId] = playButton;
    }
    
    // 如果是同一首歌
    if (audioPlayer.dataset.currentSong == songId) {
        // 更新当前按钮引用
        currentPlayButton = allPlayButtons[songId];
        
        // 如果正在播放，则暂停
        if (!audioPlayer.paused) {
            audioPlayer.pause();
        } else {
            // 如果已暂停，则继续播放
            audioPlayer.play();
        }
        return;
    }
    
    // 获取歌曲信息
    fetch(`/api/song/${songId}`)
        .then(response => response.json())
        .then(data => {
            // 先暂停当前播放
            audioPlayer.pause();
            
            // 更新播放器信息
            updatePlayerInfo(data);
            
            // 设置音频源
            audioPlayer.src = data.file_path;
            audioPlayer.dataset.currentSong = songId;
            audioPlayer.load();
            
            // 显示播放器
            playerContainer.style.display = 'block';
            
            // 更新当前播放按钮
            updateCurrentPlayButton(allPlayButtons[songId]);
            
            // 播放音频
            const playPromise = audioPlayer.play();
            if (playPromise !== undefined) {
                playPromise.catch(error => {
                    console.error('播放失败:', error);
                });
            }
        })
        .catch(error => {
            console.error('获取歌曲信息失败:', error);
        });
}

// 更新播放器信息
function updatePlayerInfo(songData) {
    const playerTitle = document.getElementById('player-title');
    const playerArtist = document.getElementById('player-artist');
    const playerCover = document.getElementById('player-cover');
    
    if (playerTitle) {
        playerTitle.textContent = `${window.APP_I18N?.now_playing || '正在播放:'} ${songData.title}`;
    }
    
    if (playerArtist) {
        let artistText = songData.artist;
        if (songData.album) {
            artistText += ` - ${window.APP_I18N?.album_label || '专辑:'} ${songData.album}`;
        }
        playerArtist.textContent = artistText;
    }
    
    if (playerCover && songData.cover_image) {
        playerCover.src = songData.cover_image;
        playerCover.style.display = 'block';
    } else if (playerCover) {
        playerCover.style.display = 'none';
    }
}

// 更新当前播放按钮
function updateCurrentPlayButton(newButton) {
    // 重置之前的按钮
    if (currentPlayButton && currentPlayButton !== newButton) {
        resetPlayButton(currentPlayButton);
    }
    
    currentPlayButton = newButton;
    
    if (currentPlayButton) {
        updatePlayButtonState(currentPlayButton, true);
    }
}

// 更新播放按钮状态
function updatePlayButtonState(button, isPlaying) {
    if (!button) return;
    
    const icon = button.querySelector('i');
    if (isPlaying) {
        button.innerHTML = button.innerHTML.replace('fa-play', 'fa-pause');
        button.innerHTML = button.innerHTML.replace('播放', '暂停').replace('Play', 'Pause');
    } else {
        button.innerHTML = button.innerHTML.replace('fa-pause', 'fa-play');
        button.innerHTML = button.innerHTML.replace('暂停', '播放').replace('Pause', 'Play');
    }
}

// 重置播放按钮
function resetPlayButton(button) {
    if (!button) return;
    
    button.innerHTML = button.innerHTML.replace('fa-pause', 'fa-play');
    button.innerHTML = button.innerHTML.replace('暂停', '播放').replace('Pause', 'Play');
}

// 音频事件监听 & 其他 DOM 事件
document.addEventListener('DOMContentLoaded', function() {
    const audioPlayer = document.getElementById('main-audio');
    
    if (audioPlayer) {
        // 播放事件
        audioPlayer.addEventListener('play', function() {
            if (currentPlayButton) {
                updatePlayButtonState(currentPlayButton, true);
            }
        });
        
        // 暂停事件
        audioPlayer.addEventListener('pause', function() {
            if (currentPlayButton) {
                updatePlayButtonState(currentPlayButton, false);
            }
        });
        
        // 播放结束事件
        audioPlayer.addEventListener('ended', function() {
            if (currentPlayButton) {
                resetPlayButton(currentPlayButton);
                currentPlayButton = null;
            }
        });
        
        // 错误事件
        audioPlayer.addEventListener('error', function(e) {
            console.error('音频播放错误:', e);
            alert(window.APP_I18N?.audio_error || '音频播放出错，请检查文件格式。');
            
            if (currentPlayButton) {
                resetPlayButton(currentPlayButton);
                currentPlayButton = null;
            }
        });
    }

    // 删除表单确认
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const msg = this.dataset.confirm || (window.APP_I18N?.delete_confirm || 'Are you sure you want to delete this item?');
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });

    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

    document.addEventListener('click', function (e) {
        const btn = e.target.closest('[data-bs-target="#addToPlaylistModal"][data-song-id]');
        if (!btn) return;

        const songId = btn.dataset.songId;
        const modalSongInput = document.getElementById('modalSongId');
        if (modalSongInput) {
            modalSongInput.value = songId;
        }
    });

    const addToPlaylistForm = document.getElementById('addToPlaylistForm');
    if (addToPlaylistForm) {
        addToPlaylistForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const songIdInput = document.getElementById('modalSongId');
            const playlistSelect = document.getElementById('playlistSelect');
            const songId = songIdInput ? songIdInput.value : '';
            const playlistId = playlistSelect ? playlistSelect.value : '';

            if (!playlistId) {
                alert('请选择一个播放列表');
                return;
            }

            fetch('/api/add_to_playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    song_id: songId,
                    playlist_id: playlistId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data && data.message) {
                    alert(data.message);
                }
                const modalEl = document.getElementById('addToPlaylistModal');
                if (modalEl && window.bootstrap) {
                    const modalInstance = window.bootstrap.Modal.getInstance(modalEl) || new window.bootstrap.Modal(modalEl);
                    modalInstance.hide();
                }
            })
            .catch(error => {
                console.error('Error adding to playlist:', error);
                alert('添加到播放列表失败，请稍后重试');
            });
        });
    }
});

// 兼容旧的播放按钮点击事件
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('play-btn') || e.target.closest('.play-btn')) {
        const button = e.target.classList.contains('play-btn') ? e.target : e.target.closest('.play-btn');
        const songId = button.dataset.songId;
        
        if (songId) {
            e.preventDefault();
            playAudio(songId);
        }
    }
});