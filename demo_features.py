#!/usr/bin/env python3
"""
演示新增的评论和互动功能
"""

from app import create_app, db
from app.models import User, Song, Comment, Favorite

def demo_new_features():
    app = create_app()
    
    with app.app_context():
        print("音乐网站新功能演示")
        print("=" * 50)
        
        # 检查现有数据
        users_count = User.query.count()
        songs_count = Song.query.filter_by(visibility='public').count()
        comments_count = Comment.query.count()
        favorites_count = Favorite.query.count()
        
        print(f"当前数据统计:")
        print(f"   用户数量: {users_count}")
        print(f"   公开歌曲: {songs_count}")
        print(f"   评论数量: {comments_count}")
        print(f"   收藏数量: {favorites_count}")
        print()
        
        # 显示最新的公开歌曲
        print("最新公开歌曲:")
        latest_songs = Song.query.filter_by(visibility='public').order_by(Song.upload_date.desc()).limit(5).all()
        
        for i, song in enumerate(latest_songs, 1):
            comments_count = song.comments.count()
            print(f"   {i}. {song.title} - {song.artist}")
            print(f"      上传者: {song.uploader.username}")
            print(f"      播放次数: {song.play_count}")
            print(f"      收藏数: {song.likes_count}")
            print(f"      评论数: {comments_count}")
            print(f"      详情页面: /song/{song.id}")
            print()
        
        # 显示最新评论
        print("最新评论:")
        latest_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
        
        for i, comment in enumerate(latest_comments, 1):
            print(f"   {i}. {comment.author.username} 评论了 '{comment.song.title}':")
            print(f"      \"{comment.content}\"")
            print(f"      时间: {comment.created_at.strftime('%Y-%m-%d %H:%M')}")
            print()
        
        # 显示用户统计
        print("用户互动统计:")
        users = User.query.all()
        
        for user in users:
            public_songs = user.uploaded_songs.filter_by(visibility='public').count()
            favorites = user.favorites.count()
            comments = user.comments.count()
            followers = user.get_followers_count()
            following = user.get_following_count()
            
            if public_songs > 0 or favorites > 0 or comments > 0:
                print(f"   {user.username}:")
                print(f"      上传歌曲: {public_songs}")
                print(f"      收藏歌曲: {favorites}")
                print(f"      发表评论: {comments}")
                print(f"      粉丝数: {followers}")
                print(f"      关注数: {following}")
                print(f"      个人页面: /user/{user.username}")
                print()
        
        print("新功能使用指南:")
        print("   1. 访问 /library 浏览所有公开音乐")
        print("   2. 点击歌曲标题进入详情页面")
        print("   3. 在详情页面可以:")
        print("      - 播放音乐")
        print("      - 收藏/取消收藏")
        print("      - 发表评论")
        print("      - 查看其他用户评论")
        print("   4. 访问 /favorites 查看收藏的歌曲")
        print("   5. 点击用户名访问用户个人页面")
        print()
        
        print("功能亮点:")
        print("   - 实时评论系统")
        print("   - 收藏功能")
        print("   - 播放次数统计")
        print("   - 用户社交功能")
        print("   - 响应式设计")
        print("   - 多语言支持")

if __name__ == '__main__':
    demo_new_features()