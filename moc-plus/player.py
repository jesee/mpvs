import subprocess
import os

class Player:
    """
    一个回归本源的、使用 subprocess 直接调用 mpv 的简单播放器。
    这个版本只关心最核心的播放功能，以确保最大的稳定性和兼容性。
    """
    def __init__(self):
        self.process = None

    def play(self, filepath: str):
        """
        播放一个文件。如果已有歌曲在播放，会先停止。
        """
        self.stop()
        
        if not os.path.exists(filepath):
            return

        # 使用最基础、最可靠的方式启动 mpv
        self.process = subprocess.Popen(
            ['mpv', filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def stop(self):
        """
        停止播放（通过终止 mpv 进程）。
        """
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def quit(self):
        """
        退出播放器时，确保停止所有播放。
        """
        self.stop()

    def toggle_pause(self):
        """
        在这个简单的模式下，暂停功能是不可用的。
        """
        # 明确地不执行任何操作
        pass