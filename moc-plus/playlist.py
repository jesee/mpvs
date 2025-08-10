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

    def load_m3u(self, filepath: str):
        """从 .m3u 文件加载播放列表。"""
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
                        # 如果没有从 #EXTINF 解析出标题，则使用文件名
                        if not title:
                            title = os.path.splitext(os.path.basename(path))[0]
                        self.songs.append(Song(title=title, path=path))
                    title = "" # 重置标题

    def save_m3u(self, filepath: str):
        """将当前播放列表保存到 .m3u 文件。"""
        # 确保目录存在
        dir_path = os.path.dirname(filepath)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            # M3U 文件的标准头部
            f.write('#EXTM3U\n')
            for song in self.songs:
                # 写入扩展信息（可选，但更标准）
                f.write(f'#EXTINF:-1,{song.title}\n')
                # 写入文件路径
                f.write(f'{song.path}\n')

    def load_m3u(self, filepath: str):
        """从 .m3u 文件加载播放列表。"""
        self.songs.clear()
        self.current_selection_index = 0
        
        if not os.path.exists(filepath):
            return # 文件不存在，则加载一个空列表

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#EXTM3U'):
                    continue
                
                # 如果是文件路径行
                if not line.startswith('#'):
                    path = line
                    # 尝试从前一行 #EXTINF 中解析标题
                    title = os.path.splitext(os.path.basename(path))[0]
                    self.songs.append(Song(title=title, path=path))

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
