import curses

def setup_colors():
    """初始化颜色配对"""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)  # Default
    curses.init_pair(2, curses.COLOR_CYAN, -1)   # Border
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_GREEN)  # Status bar

def draw_layout(stdscr, main_win, status_win):
    """
    绘制静态UI布局，如边框和标题。
    """
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    main_win.clear()
    
    # 绘制主窗口边框
    main_win.box()
    
    # 绘制标题
    title = " MOC-Plus Terminal Player "
    main_win.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)

    # 绘制一个临时的帮助信息
    help_text = "Press 'q' to quit"
    # 注意：窗口坐标相对于窗口本身，不是stdscr
    main_height, main_width = main_win.getmaxyx()
    main_win.addstr(main_height // 2, (main_width - len(help_text)) // 2, help_text)

    stdscr.refresh()
    main_win.refresh()

def update_status(status_win):
    """
    更新状态栏内容。
    """
    status_win.clear()
    status_text = "STATUS: Idle | Press 'q' to quit"
    
    # 设置背景色并添加文本
    status_win.bkgd(' ', curses.color_pair(3))
    status_win.addstr(0, 1, status_text)
    
    status_win.refresh()