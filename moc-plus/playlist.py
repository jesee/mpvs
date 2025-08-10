import os
from dataclasses import dataclass, field

SUPPORTED_EXTENSIONS = ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a']

@dataclass
class Song:
    """一个简单的数据类，用于存储歌曲信息。"""
    title: str
    path: str

@dataclass
class Playlist:
    """管理歌曲列表和当前选择。"""
    songs: list[Song] = field(default_factory=list)
    current_selection_index: int = 0

    def scan_directory(self, path: str):
        """
        扫描指定目录及其子目录，查找支持的音频文件。
        """
        self.songs.clear()
        try:
            for root, _, files in os.walk(path):
                for filename in sorted(files):
                    if any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                        full_path = os.path.join(root, filename)
                        # 使用文件名作为标题（去掉扩展名）
                        title = os.path.splitext(filename)[0]
                        self.songs.append(Song(title=title, path=full_path))
        except FileNotFoundError:
            # 如果目录不存在，播放列表为空，程序不会崩溃
            pass
        
        self.current_selection_index = 0

    def get_current_song(self) -> Song | None:
        """获取当前选中的歌曲。"""
        if not self.songs:
            return None
        return self.songs[self.current_selection_index]

    def select_next(self):
        """移动选择到下一首歌曲。"""
        if not self.songs:
            return
        self.current_selection_index = (self.current_selection_index + 1) % len(self.songs)

    def select_previous(self):
        """移动选择到上一首歌曲。"""
        if not self.songs:
            return
        self.current_selection_index = (self.current_selection_index - 1 + len(self.songs)) % len(self.songs)

if __name__ == '__main__':
    # --- 测试 Playlist 模块 ---
    playlist = Playlist()
    
    # 假设我们的音乐在上一级的 '斗破苍穹' 文件夹中
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '斗破苍穹'))
    print(f"Scanning directory: {test_dir}")
    playlist.scan_directory(test_dir)

    if not playlist.songs:
        print("No songs found in the directory.")
    else:
        print(f"Found {len(playlist.songs)} songs:")
        for i, song in enumerate(playlist.songs):
            print(f"  {i+1}. {song.title} ({song.path})")

        print(f"\nInitial selection: {playlist.get_current_song().title}")
        playlist.select_next()
        print(f"After selecting next: {playlist.get_current_song().title}")
        playlist.select_previous()
        print(f"After selecting previous: {playlist.get_current_song().title}")
