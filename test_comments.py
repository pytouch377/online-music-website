#!/usr/bin/env python3
"""
测试评论和互动功能
"""

from app import create_app, db
from app.models import User, Song, Comment, Favorite

def test_comments_and_interactions():
    app = create_app()
    
    with app.app_context():
        # 创建测试用户
        user1 = User(username='testuser1', email='test1@example.com')
        user1.set_password('password123')
        
        user2 = User(username='testuser2', email='test2@example.com')
        user2.set_password('password123')
        
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        
        # 创建测试歌曲
        song = Song(
            title='测试歌曲',
            artist='测试艺术家',
            album='测试专辑',
            file_path='uploads/audio/test.mp3',
            user_id=user1.id,
            visibility='public'
        )
        
        db.session.add(song)
        db.session.commit()
        
        # 测试评论功能
        comment1 = Comment(
            content='这首歌真不错！',
            user_id=user2.id,
            song_id=song.id
        )
        
        comment2 = Comment(
            content='我也很喜欢这首歌',
            user_id=user1.id,
            song_id=song.id
        )
        
        db.session.add(comment1)
        db.session.add(comment2)
        db.session.commit()
        
        # 测试收藏功能
        favorite = Favorite(
            user_id=user2.id,
            song_id=song.id
        )
        
        db.session.add(favorite)
        song.likes_count += 1
        db.session.commit()
        
        # 验证数据
        print(f"歌曲: {song.title}")
        print(f"评论数量: {song.comments.count()}")
        print(f"收藏数量: {song.likes_count}")
        
        for comment in song.comments:
            print(f"评论: {comment.content} - 作者: {comment.author.username}")
        
        print("测试完成！")

if __name__ == '__main__':
    test_comments_and_interactions()