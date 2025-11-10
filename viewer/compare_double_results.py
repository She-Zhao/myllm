"""
LLM 结果对比浏览器

使用 PyQt5 可视化并排比较两个 JSONL 文件中的模型输出。

功能:
- 加载两个 .jsonl 文件。
- 自动匹配两个文件中 'id' 相同的条目。
- 顶部显示共享的图像。
- 底部左右分栏显示两个文件中的 'assistant' 回复。
- 组标题显示文件名，以便区分。
- 按 'A' 键切换到上一个，按 'D' 键切换到下一个。

"""
import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore

# 💡 (复用) 沿用您满意的暗色主题 QSS
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
    (复用) 自定义的图像标签，保持长宽比。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pixmap = QtGui.QPixmap()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(400, 300) 
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def setPixmap(self, pixmap: QtGui.QPixmap):
        self._pixmap = pixmap
        self.update_pixmap()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self.update_pixmap()
        super().resizeEvent(event)

    def update_pixmap(self):
        if self._pixmap.isNull():
            super().setPixmap(QtGui.QPixmap())
            return
            
        scaled_pixmap = self._pixmap.scaled(
            self.size(), 
            QtCore.Qt.KeepAspectRatio, 
            QtCore.Qt.SmoothTransformation
        )
        super().setPixmap(scaled_pixmap)


class ResultViewer(QtWidgets.QWidget):
    """
    主对比窗口
    """
    def __init__(self, jsonl_path1: str, jsonl_path2: str):
        super().__init__()
        
        self.records = [] # 这是一个合并后的记录列表
        self.current_index = 0
        
        # 💡 新增：保存文件名用于显示
        self.filename1 = os.path.basename(jsonl_path1)
        self.filename2 = os.path.basename(jsonl_path2)
        
        self.load_data(jsonl_path1, jsonl_path2)
        
        if not self.records:
            QtWidgets.QMessageBox.critical(self, "错误", "无法加载数据，或两个文件没有共同的 ID。")
            QtCore.QTimer.singleShot(0, self.close)
            return

        self.init_ui()
        self.update_display()
        self.show()

    def init_ui(self):
        """
        初始化 UI 布局 (修改为对比布局)
        """
        # --- 1. 顶部：图像 ---
        self.image_label = ImageLabel()
        self.image_label.setText("正在加载图像...")

        # --- 2. 底部：文本 (左右分割) ---
        
        # 💡 修改：左侧显示文件1的回复
        self.group_1 = QtWidgets.QGroupBox(f"文件 A: {self.filename1}")
        layout_1 = QtWidgets.QVBoxLayout()
        self.text_area_1 = QtWidgets.QTextEdit()
        self.text_area_1.setReadOnly(True)
        layout_1.addWidget(self.text_area_1)
        self.group_1.setLayout(layout_1)
        layout_1.setContentsMargins(10, 10, 10, 10)

        # 💡 修改：右侧显示文件2的回复
        self.group_2 = QtWidgets.QGroupBox(f"文件 B: {self.filename2}")
        layout_2 = QtWidgets.QVBoxLayout()
        self.text_area_2 = QtWidgets.QTextEdit()
        self.text_area_2.setReadOnly(True)
        layout_2.addWidget(self.text_area_2)
        self.group_2.setLayout(layout_2)
        layout_2.setContentsMargins(10, 10, 10, 10)

        # 2c. 分割器
        self.text_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.text_splitter.addWidget(self.group_1)
        self.text_splitter.addWidget(self.group_2)
        self.text_splitter.setSizes([400, 400])

        # --- 3. 整体布局 (上下分割) ---
        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.main_splitter.addWidget(self.image_label)
        self.main_splitter.addWidget(self.text_splitter)
        self.main_splitter.setSizes([600, 400])

        # --- 4. 设置为主窗口布局 ---
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.main_splitter)
        self.setLayout(main_layout)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- 5. 窗口设置 ---
        self.setGeometry(100, 100, 1200, 900)
        self.setWindowTitle("LLM 结果对比浏览器")

    def load_data(self, jsonl_path1: str, jsonl_path2: str):
        """
        💡 新增：加载两个文件，并按 ID 匹配
        """
        data_map1 = {}
        data_map2 = {}

        # --- 加载文件 1 ---
        print(f"正在加载文件 1: {self.filename1}")
        try:
            with open(jsonl_path1, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        data_map1[record['id']] = record
                    except (json.JSONDecodeError, KeyError):
                        print(f"警告: 跳过文件1中无法解析或缺少'id'的行: {line[:50]}...")
        except FileNotFoundError:
            print(f"错误: 文件未找到 {jsonl_path1}")
            return # 无法继续
        
        # --- 加载文件 2 ---
        print(f"正在加载文件 2: {self.filename2}")
        try:
            with open(jsonl_path2, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        data_map2[record['id']] = record
                    except (json.JSONDecodeError, KeyError):
                        print(f"警告: 跳过文件2中无法解析或缺少'id'的行: {line[:50]}...")
        except FileNotFoundError:
            print(f"错误: 文件未找到 {jsonl_path2}")
            return # 无法继续

        # --- 匹配共同 ID ---
        common_ids = set(data_map1.keys()) & set(data_map2.keys())
        print(f"加载完成，共找到 {len(common_ids)} 个共同 ID。")

        # --- 构建合并后的记录列表 ---
        for common_id in sorted(list(common_ids)): # 排序以保证顺序
            try:
                record1 = data_map1[common_id]
                record2 = data_map2[common_id]
                
                # 假设 image 路径相同，取文件1的
                image_path = record1['image']
                
                merged_record = {
                    'id': common_id,
                    'image': image_path,
                    'answer_1': record1['conversation'][1]['value'], # 文件1的回复
                    'answer_2': record2['conversation'][1]['value']  # 文件2的回复
                }
                self.records.append(merged_record)
                
            except Exception as e:
                print(f"警告: 合并 ID {common_id} 时出错 (数据可能不完整): {e}")

    def update_display(self):
        """
        💡 修改：根据 self.records 的新结构更新显示
        """
        if not (0 <= self.current_index < len(self.records)):
            return
            
        record = self.records[self.current_index]

        # --- 更新图像 ---
        try:
            image_path = record['image'][0] # 仍然取列表的第一个
            pixmap = QtGui.QPixmap(image_path)
            if pixmap.isNull():
                self.image_label.setText(f"无法加载图像:\n{image_path}")
                self.image_label.setPixmap(QtGui.QPixmap())
            else:
                self.image_label.setPixmap(pixmap)
        except Exception as e:
            self.image_label.setText(f"加载图像时出错:\n{e}")
            self.image_label.setPixmap(QtGui.QPixmap())

        # --- 更新文本 (不再显示 human) ---
        self.text_area_1.setText(record.get('answer_1', "** 加载失败 **"))
        self.text_area_2.setText(record.get('answer_2', "** 加载失败 **"))
            
        # --- 更新窗口标题 ---
        self.setWindowTitle(f"对比浏览器 ({self.current_index + 1}/{len(self.records)}) - ID: {record['id']}")

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """
        (复用) 处理 'A' 和 'D' 键按下事件
        """
        key = event.key()

        if key == QtCore.Qt.Key_A:
            self.prev_item()
        elif key == QtCore.Qt.Key_D:
            self.next_item()
        else:
            super().keyPressEvent(event)

    def prev_item(self):
        """
        (复用) 切换到上一个项目
        """
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
        else:
            print("已是第一条。")

    def next_item(self):
        """
        (复用) 切换到下一个项目
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
    
    app.setStyleSheet(APP_STYLESHEET)
    font = QtGui.QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 💡 --- 修改开始 ---
    # 1. 弹出文件选择框，选择第一个文件
    jsonl_path1, _ = QtWidgets.QFileDialog.getOpenFileName(
        None, 
        "请选择第一个 .jsonl 文件 (文件 A)", 
        "", 
        "JSONL Files (*.jsonl);;All Files (*)"
    )
    
    # 检查用户是否取消了第一个选择
    if not jsonl_path1:
        print("未选择第一个文件，程序退出。")
        sys.exit(0)

    # 2. 弹出文件选择框，选择第二个文件
    jsonl_path2, _ = QtWidgets.QFileDialog.getOpenFileName(
        None, 
        "请选择第二个 .jsonl 文件 (文件 B)", 
        # 默认打开与第一个文件相同的目录，方便操作
        os.path.dirname(jsonl_path1), 
        "JSONL Files (*.jsonl);;All Files (*)"
    )
    
    # 检查用户是否取消了第二个选择
    if not jsonl_path2:
        print("未选择第二个文件，程序退出。")
        sys.exit(0)

    # 3. 检查是否选择了同一个文件
    if jsonl_path1 == jsonl_path2:
        msg_box = QtWidgets.QMessageBox()
        msg_box.setStyleSheet(APP_STYLESHEET)
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("选择错误")
        msg_box.setText("您选择了同一个文件两次。请选择两个不同的文件进行比较。")
        msg_box.exec_()
        print("用户选择了同一个文件，程序退出。")
        sys.exit(0)

    # 4. 启动对比窗口
    print(f"文件 A: {jsonl_path1}")
    print(f"文件 B: {jsonl_path2}")
    viewer = ResultViewer(jsonl_path1, jsonl_path2)
    sys.exit(app.exec_())
    # 💡 --- 修改结束 ---


if __name__ == "__main__":
    main()