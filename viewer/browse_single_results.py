"""
SFT / LLM 结果浏览器

使用 PyQt5 可视化 JSONL 文件中的多模态数据。

功能:
- 加载 .jsonl 文件。
- 顶部显示图像 (来自 'image' 字段的路径)。
- 底部左右分栏显示 'human' 提示词和 'assistant' 回复。
- 图像会自适应窗口大小，保持长宽比。
- 按 'A' 键切换到上一个，按 'D' 键切换到下一个。

作者: 这是gemini写的（出错了我也不知道哪有问题……）
"""
import sys
import json
from PyQt5 import QtWidgets, QtGui, QtCore

# 💡 美化第一步：定义 QSS 样式表 (类似 CSS)
# 这是一个简洁的暗色主题
APP_STYLESHEET = """
QWidget {
    background-color: #2E2E2E; /* 深灰色背景 */
    color: #E0E0E0;            /* 浅灰色字体 */
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; /* 优先使用微软雅黑 */
}

QSplitter::handle {
    background-color: #4A4A4A; /* 分割器手柄颜色 */
    border: 1px solid #3c3c3c;
}

QSplitter::handle:vertical {
    height: 8px;
}

QSplitter::handle:horizontal {
    width: 8px;
}

QGroupBox {
    background-color: #383838; /* GroupBox 背景 */
    border: 1px solid #505050;
    border-radius: 6px;
    margin-top: 10px; /* 为标题留出空间 */
    font-size: 14px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
    background-color: #4A4A4A;
    color: #FFFFFF;
    border-radius: 4px;
}

QTextEdit {
    background-color: #252525; /* 文本框背景 */
    color: #F0F0F0;
    border: 1px solid #505050;
    border-radius: 4px;
    font-size: 13pt; /* 💡 美化：增大文本框字体 */
    padding: 8px;
}

QLabel {
    background-color: #202020; /* 图像标签背景 (更暗) */
    border: 1px solid #505050;
    border-radius: 6px;
    font-size: 16px; /* 加载提示的字体 */
    color: #888888; /* 加载提示的颜色 */
}

QScrollBar:vertical {
    border: 1px solid #4A4A4A;
    background: #383838;
    width: 15px;
    margin: 15px 0 15px 0;
}
QScrollBar::handle:vertical {
    background: #606060;
    min-height: 20px;
    border-radius: 7px;
}

QScrollBar:horizontal {
    border: 1px solid #4A4A4A;
    background: #383838;
    height: 15px;
    margin: 0 15px 0 15px;
}
QScrollBar::handle:horizontal {
    background: #606060;
    min-width: 20px;
    border-radius: 7px;
}

QMessageBox {
    background-color: #383838;
}

/* 确保文件对话框在某些系统上也应用样式 */
QFileDialog {
    background-color: #383838;
}
QFileDialog QListView {
    background-color: #252525;
}
"""

class ImageLabel(QtWidgets.QLabel):
    """
    一个自定义的 QLabel, 它可以自动缩放 pixmap 以适应标签大小，
    同时保持图像的长宽比。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pixmap = QtGui.QPixmap()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(400, 300) # 设置一个最小尺寸
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def setPixmap(self, pixmap: QtGui.QPixmap):
        """
        设置 pixmap 并触发更新。
        """
        self._pixmap = pixmap
        self.update_pixmap()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        """
        当窗口/标签大小改变时，自动重新缩放图像。
        """
        self.update_pixmap()
        super().resizeEvent(event)

    def update_pixmap(self):
        """
        核心缩放逻辑：将 self._pixmap 缩放到当前标签大小并显示。
        """
        if self._pixmap.isNull():
            # 如果 pixmap 为空，清除标签
            super().setPixmap(QtGui.QPixmap())
            return
            
        # 缩放图像以适应当前标签大小，保持长宽比
        scaled_pixmap = self._pixmap.scaled(
            self.size(), 
            QtCore.Qt.KeepAspectRatio, 
            QtCore.Qt.SmoothTransformation
        )
        # 调用父类的 setPixmap 来真正显示图像
        super().setPixmap(scaled_pixmap)


class ResultViewer(QtWidgets.QWidget):
    """
    主浏览器窗口
    """
    def __init__(self, jsonl_path: str):
        super().__init__()
        
        self.records = []
        self.current_index = 0
        
        self.load_data(jsonl_path)
        if not self.records:
            # 如果加载数据失败或文件为空
            QtWidgets.QMessageBox.critical(self, "错误", "无法加载数据或文件为空。")
            # 延迟退出，否则主循环还没开始
            QtCore.QTimer.singleShot(0, self.close)
            return

        self.init_ui()
        self.update_display()
        self.show()

    def init_ui(self):
        """
        初始化 UI 布局
        """
        # --- 1. 顶部：图像 ---
        self.image_label = ImageLabel() # 使用我们自定义的 ImageLabel
        self.image_label.setText("正在加载图像...")

        # --- 2. 底部：文本 (左右分割) ---
        
        # 2a. Human 提示词
        self.human_group = QtWidgets.QGroupBox("Human 提示词 (conversation[0])")
        human_layout = QtWidgets.QVBoxLayout()
        self.human_text = QtWidgets.QTextEdit()
        self.human_text.setReadOnly(True)
        human_layout.addWidget(self.human_text)
        self.human_group.setLayout(human_layout)
        # 💡 美化：为布局添加边距
        human_layout.setContentsMargins(10, 10, 10, 10)


        # 2b. Model 回复
        self.assistant_group = QtWidgets.QGroupBox("Model 回复 (conversation[1])")
        assistant_layout = QtWidgets.QVBoxLayout()
        self.assistant_text = QtWidgets.QTextEdit()
        self.assistant_text.setReadOnly(True)
        assistant_layout.addWidget(self.assistant_text)
        self.assistant_group.setLayout(assistant_layout)
        # 💡 美化：为布局添加边距
        assistant_layout.setContentsMargins(10, 10, 10, 10)

        # 2c. 分割器
        self.text_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.text_splitter.addWidget(self.human_group)
        self.text_splitter.addWidget(self.assistant_group)
        self.text_splitter.setSizes([400, 400]) # 初始均分

        # --- 3. 整体布局 (上下分割) ---
        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.main_splitter.addWidget(self.image_label)
        self.main_splitter.addWidget(self.text_splitter)
        self.main_splitter.setSizes([600, 400]) # 初始图像占 60%

        # --- 4. 设置为主窗口布局 ---
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.main_splitter)
        self.setLayout(main_layout)
        # 💡 美化：为布局添加边距
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- 5. 窗口设置 ---
        self.setGeometry(100, 100, 1200, 900)
        self.setWindowTitle("SFT/LLM 结果浏览器")

    def load_data(self, jsonl_path: str):
        """
        从 .jsonl 文件加载数据到 self.records
        """
        print(f"正在加载文件: {jsonl_path}")
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        self.records.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(f"警告: 跳过一行无法解析的 JSON: {line[:50]}...")
        except FileNotFoundError:
            print(f"错误: 文件未找到 {jsonl_path}")
        except Exception as e:
            print(f"加载文件时发生未知错误: {e}")
            
        print(f"加载完成，共 {len(self.records)} 条数据。")

    def update_display(self):
        """
        根据 self.current_index 更新显示内容
        """
        if not (0 <= self.current_index < len(self.records)):
            return
            
        record = self.records[self.current_index]

        # --- 更新图像 ---
        try:
            # 假设 'image' 是一个列表，我们取第一个
            image_path = record['image'][0]
            pixmap = QtGui.QPixmap(image_path)
            if pixmap.isNull():
                self.image_label.setText(f"无法加载图像:\n{image_path}")
                self.image_label.setPixmap(QtGui.QPixmap()) # 清空旧图像
            else:
                self.image_label.setPixmap(pixmap)
        except Exception as e:
            self.image_label.setText(f"加载图像时出错:\n{e}")
            self.image_label.setPixmap(QtGui.QPixmap())

        # --- 更新文本 ---
        try:
            human_prompt = record['conversation'][0]['value']
            self.human_text.setText(human_prompt)
        except (IndexError, KeyError) as e:
            self.human_text.setText(f"** 无法解析 Human 提示词: {e} **")

        try:
            assistant_response = record['conversation'][1]['value']
            self.assistant_text.setText(assistant_response)
        except (IndexError, KeyError) as e:
            self.assistant_text.setText(f"** 无法解析 Assistant 回复: {e} **")
            
        # --- 更新窗口标题 ---
        self.setWindowTitle(f"结果浏览器 ({self.current_index + 1}/{len(self.records)}) - {record['id']}")

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """
        处理 'A' 和 'D' 键按下事件
        """
        key = event.key()

        if key == QtCore.Qt.Key_A:
            # 'A' 键 - 上一个
            self.prev_item()
        elif key == QtCore.Qt.Key_D:
            # 'D' 键 - 下一个
            self.next_item()
        else:
            # 其他按键交由父类处理
            super().keyPressEvent(event)

    def prev_item(self):
        """
        切换到上一个项目
        """
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
        else:
            print("已是第一条。")

    def next_item(self):
        """
        切换到下一个项目
        """
        if self.current_index < len(self.records) - 1:
            self.current_index += 1
            self.update_display()
        else:
            print("已是最后一条。")


def main():
    """
    主函数：启动应用并显示文件选择对话框
    """
    app = QtWidgets.QApplication(sys.argv)
    
    # 💡 美化第二步：应用样式表
    app.setStyleSheet(APP_STYLESHEET)
    # 💡 美化第三步：设置全局字体
    font = QtGui.QFont("Microsoft YaHei", 10) # 默认 10pt 微软雅黑
    app.setFont(font)


    # 弹出文件选择框
    jsonl_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        None, 
        "请选择 JSONL 结果文件", 
        "", 
        "JSONL Files (*.jsonl);;All Files (*)"
    )

    # 如果用户选择了文件
    if jsonl_path:
        viewer = ResultViewer(jsonl_path)
        sys.exit(app.exec_())
    else:
        print("未选择文件，程序退出。")
        sys.exit(0)

if __name__ == "__main__":
    main()
