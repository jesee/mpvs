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

    def scan_directory(self, path: str, append: bool = False):
        """
        扫描指定目录及其子目录，查找支持的音频文件。
        
        :param path: 要扫描的目录路径。
        :param append: 如果为 True，则追加到现有列表，否则覆盖。
        """
        if not append:
            self.songs.clear()
            self.current_selection_index = 0

        try:
            for root, _, files in os.walk(path):
                for filename in sorted(files):
                    if any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                        full_path = os.path.join(root, filename)
                        # 避免重复添加
                        if not any(song.path == full_path for song in self.songs):
                            title = os.path.splitext(filename)[0]
                            self.songs.append(Song(title=title, path=full_path))
        except FileNotFoundError:
            pass
        
        if not append:
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

    def save_m3u(self, filepath: str):
        """将当前播放列表保存到 .m3u 文件。"""
        dir_path = os.path.dirname(filepath)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for song in self.songs:
                f.write(f'#EXTINF:-1,{song.title}\n')
                f.write(f'{song.path}\n')

    def load_m3u(self, filepath: str, append: bool = False):
        """
        从 .m3u 文件加载播放列表。
        
        :param filepath: .m3u 文件的路径。
        :param append: 如果为 True，则追加到现有列表，否则覆盖。
        """
        if not append:
            self.songs.clear()
            self.current_selection_index = 0
        
        if not os.path.exists(filepath):
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            title = ""
            for line in f:
                line = line.strip()
                if not line or line.startswith('#EXTM3U'):
                    continue
                if line.startswith('#EXTINF:'):
                    title = line.split(',', 1)[-1]
                elif not line.startswith('#'):
                    path = line
                    if os.path.exists(path):
                        if not title:
                            title = os.path.splitext(os.path.basename(path))[0]
                        if not any(song.path == path for song in self.songs):
                            self.songs.append(Song(title=title, path=path))
                    title = ""

    def delete_song(self, index: int):
        """按索引删除一首歌曲。"""
        if 0 <= index < len(self.songs):
            del self.songs[index]

    def clear(self):
        """清空整个播放列表。"""
        self.songs.clear()
        self.current_selection_index = 0

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
