import os
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, ListView, ListItem, Static

class FileBrowserScreen(Screen):
    """一个扁平的、类似 mocp 的文件/目录列表浏览器。"""
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("a", "add_to_playlist", "Add to Playlist"),
    ]

    def __init__(self, start_path: str = "~"):
        super().__init__()
        self.current_path = Path(start_path).expanduser().resolve()

    def compose(self) -> ComposeResult:
        yield Header(name="File Browser")
        yield ListView(id="dir_list")
        yield Footer()

    def on_mount(self) -> None:
        self.load_directory()

    def load_directory(self):
        """读取当前路径并填充 ListView。"""
        self.sub_title = str(self.current_path)
        list_view = self.query_one(ListView)
        list_view.clear()

        # 定义我们关心的文件扩展名
        music_extensions = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".m3u"}

        # 添加返回上级目录的选项
        parent_item = ListItem(Static("[..]"))
        parent_item.data = self.current_path.parent
        list_view.append(parent_item)

        items = []
        try:
            for item_path in sorted(self.current_path.iterdir()):
                # 忽略隐藏文件和文件夹
                if item_path.name.startswith('.'):
                    continue

                if item_path.is_dir():
                    list_item = ListItem(Static(f"[D] {item_path.name}"))
                    list_item.data = item_path
                    items.append(list_item)
                elif item_path.is_file():
                    if item_path.suffix.lower() in music_extensions:
                        list_item = ListItem(Static(f"[F] {item_path.name}"))
                        list_item.data = item_path
                        items.append(list_item)
        except OSError:
            pass
        
        list_view.extend(items)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """当用户按回车时调用。"""
        if hasattr(event.item, 'data'):
            path_to_load = event.item.data
            if path_to_load and path_to_load.is_dir():
                self.current_path = path_to_load
                self.load_directory()

    def action_add_to_playlist(self) -> None:
        """当用户按下 'a' 键时调用。"""
        list_view = self.query_one(ListView)
        if list_view.highlighted_child and hasattr(list_view.highlighted_child, 'data'):
            path_to_add = list_view.highlighted_child.data
            self.app.add_path_to_playlist(str(path_to_add))