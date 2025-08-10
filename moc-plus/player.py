import subprocess
import os

class Player:
    """
    一个使用 subprocess 直接调用 mpv 的简单播放器。
    这种方法牺牲了精细控制，但换取了最大的稳定性，避免了事件循环冲突。
    """
    def __init__(self):
        self.process = None

    def play(self, filepath: str):
        """
        播放一个文件。如果已有歌曲在播放，会先停止。
        """
        if self.process:
            self.stop()
        
        # 确保文件存在
        if not os.path.exists(filepath):
            return

        # 使用 subprocess.Popen 启动一个完全独立的 mpv 进程
        # 我们将 stdout 和 stderr 重定向，以避免它们干扰我们的 TUI
        self.process = subprocess.Popen(
            ['mpv', filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def stop(self):
        """
        停止播放（通过终止 mpv 进程）。
        """
        if self.process:
            self.process.terminate()
            try:
                # 等待一小段时间确保进程已终止
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                # 如果没有正常终止，就强制杀死
                self.process.kill()
            self.process = None

    def quit(self):
        """
        退出播放器时，确保停止所有播放。
        """
        self.stop()