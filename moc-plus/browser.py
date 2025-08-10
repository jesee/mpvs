from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import DirectoryTree, Footer, Header
import os

class FileBrowserScreen(Screen):
    """一个用于浏览文件系统并与播放列表交互的屏幕。"""
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("a", "add_to_playlist", "Add to Playlist"),
    ]

    def compose(self) -> ComposeResult:
        """创建此屏幕的组件。"""
        yield Header(name="File Browser")
        # 使用 Textual 内置的 DirectoryTree 组件
        yield DirectoryTree(os.path.expanduser("~"), id="dir_tree")
        yield Footer()

    def action_add_to_playlist(self) -> None:
        """当用户按下 'a' 键时调用。"""
        tree = self.query_one(DirectoryTree)
        if not tree.cursor_node:
            return

        path = tree.cursor_node.data.path
        
        # 通过主应用的回调来处理添加逻辑
        # 这是一个健壮的设计，避免了屏幕直接修改播放列表
        self.app.add_path_to_playlist(str(path))
