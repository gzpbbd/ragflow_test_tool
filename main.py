import sys
import time
import json
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QTextEdit, 
                           QPushButton, QProgressBar, QGridLayout, QTableWidget,
                           QTableWidgetItem, QHeaderView, QSplitter, QFileDialog,
                           QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import requests
import pandas as pd


class APIClient:
    """API客户端，用于发送HTTP请求"""
    
    def __init__(self, base_url, token, agent_id):
        """
        初始化API客户端
        
        Args:
            base_url (str): API基础URL
            token (str): 认证令牌
            agent_id (str): 代理ID
        """
        self.base_url = base_url
        self.token = token
        self.agent_id = agent_id
        self.logger = logging.getLogger("APIClient")
        
    def create_session(self):
        """
        创建对话session
        
        Returns:
            str: session_id
        """
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/sessions"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Python/1.0.0",
            "Accept": "*/*",
            "Host": self.base_url.split("://")[1],
            "Connection": "keep-alive"
        }
        
        self.logger.info(f"正在创建新会话...")
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            session_id = response.json()["data"]["id"]
            self.logger.info(f"会话创建成功，session_id: {session_id}")
            return session_id
        except Exception as e:
            error_msg = f"创建session失败: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
    def send_question(self, question):
        """
        发送单个问题到API
        
        Args:
            question (str): 问题文本
            
        Returns:
            dict: API响应
        """
        try:
            # 第一步：创建session
            self.logger.info(f"准备发送问题: {question}")
            session_id = self.create_session()
            
            # 第二步：发送问题获取回答
            url = f"{self.base_url}/api/v1/agents/{self.agent_id}/completions"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "Python/1.0.0",
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Host": self.base_url.split("://")[1],
                "Connection": "keep-alive"
            }
            
            payload = {
                "question": question,
                "stream": False,
                "session_id": session_id
            }
            
            self.logger.info(f"正在请求答案...")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            answer = response.json()["data"]["answer"]
            self.logger.info(f"收到回答，长度: {len(answer)} 字符")
            
            return {
                "question": question,
                "answer": answer,
                "session_id": session_id,
                "timestamp": time.time()
            }
            
        except Exception as e:
            error_msg = f"处理问题失败: {str(e)}"
            self.logger.error(error_msg)
            return {
                "question": question,
                "error": error_msg,
                "timestamp": time.time()
            }


class RequestWorker(QThread):
    """工作线程，用于发送HTTP请求"""
    update_progress = pyqtSignal(int, str, float)  # 进度百分比, 当前处理的问题, 耗时
    complete = pyqtSignal(list)  # 所有响应结果的列表
    log_message = pyqtSignal(str)  # 日志消息

    def __init__(self, questions, base_url, token, agent_id):
        super().__init__()
        self.questions = questions
        self.api_client = APIClient(base_url, token, agent_id)
        self.results = []
        
        # 设置日志处理
        self.logger = logging.getLogger("RequestWorker")
        self.api_client.logger = self.logger
        
        # 添加日志处理器，将日志发送到界面
        class QTextEditHandler(logging.Handler):
            def __init__(self, signal):
                super().__init__()
                self.signal = signal
            
            def emit(self, record):
                msg = self.format(record)
                self.signal.emit(msg)
        
        handler = QTextEditHandler(self.log_message)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                   datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def run(self):
        total = len(self.questions)
        self.logger.info(f"开始处理 {total} 个问题")
        
        for i, question in enumerate(self.questions):
            start_time = time.time()
            
            # 发送请求
            self.logger.info(f"处理第 {i+1}/{total} 个问题")
            response = self.api_client.send_question(question)
            
            elapsed_time = time.time() - start_time
            self.results.append({
                'question': question,
                'response': response,
                'time': elapsed_time
            })
            
            # 更新进度
            progress_percentage = int((i + 1) / total * 100)
            self.update_progress.emit(progress_percentage, question, elapsed_time)
        
        self.logger.info("所有问题处理完成")
        self.complete.emit(self.results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("问题批量测试工具")
        self.setGeometry(100, 50, 1600, 900)
        self.setup_ui()
        self.qa_results = []  # 存储所有问答结果

    def setup_ui(self):
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)  # 增加组件之间的间距
        main_layout.setContentsMargins(10, 10, 10, 10)  # 设置边距
        
        # 设置区域 - 使用水平布局
        settings_widget = QWidget()
        settings_layout = QHBoxLayout(settings_widget)
        settings_layout.setSpacing(20)  # 增加设置项之间的间距
        
        # Base URL
        url_layout = QVBoxLayout()
        url_layout.addWidget(QLabel("Base URL:"))
        self.base_url_input = QLineEdit("https://ragflow.ai-t.wtvdev.com")
        self.base_url_input.setMinimumWidth(400)  # 设置最小宽度
        url_layout.addWidget(self.base_url_input)
        settings_layout.addLayout(url_layout)
        
        # Token
        token_layout = QVBoxLayout()
        token_layout.addWidget(QLabel("Token:"))
        self.token_input = QLineEdit("ragflow-IyMDZlNjVhZWE4NDExZWY5MTdhMDI0Mm")
        self.token_input.setMinimumWidth(400)
        token_layout.addWidget(self.token_input)
        settings_layout.addLayout(token_layout)
        
        # Agent ID
        agent_layout = QVBoxLayout()
        agent_layout.addWidget(QLabel("Agent ID:"))
        self.agent_id_input = QLineEdit("68417640f99611efbabb0242ac130006")
        self.agent_id_input.setMinimumWidth(300)
        agent_layout.addWidget(self.agent_id_input)
        settings_layout.addLayout(agent_layout)
        
        main_layout.addWidget(settings_widget)
        
        # 创建水平分割器
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")  # 设置分隔条样式
        
        # 左侧区域（问题输入和控制）
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)
        
        # 问题列表输入区
        question_label = QLabel("问题列表（每行一个问题）:")
        question_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        left_layout.addWidget(question_label)
        
        self.questions_input = QTextEdit()
        self.questions_input.setPlaceholderText("请在此输入问题，每行一个...")
        self.questions_input.setStyleSheet("font-size: 11pt;")
        self.questions_input.setMinimumHeight(300)  # 增加文本框高度
        # 设置默认问题列表
        default_questions = "你是谁\n文旅卡是什么\n杭州有哪些景点"
        self.questions_input.setText(default_questions)
        left_layout.addWidget(self.questions_input)
        
        # 运行按钮
        self.run_button = QPushButton("开始测试")
        self.run_button.setStyleSheet("""
            QPushButton {
                font-size: 12pt;
                padding: 8px;
                min-width: 120px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.run_button.clicked.connect(self.start_testing)
        left_layout.addWidget(self.run_button)
        
        # 进度条和状态
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("font-size: 11pt;")
        progress_layout.addWidget(self.status_label)
        left_layout.addLayout(progress_layout)
        
        # 当前执行信息
        self.current_question_label = QLabel("当前问题: ")
        self.current_question_label.setStyleSheet("font-size: 11pt;")
        left_layout.addWidget(self.current_question_label)
        self.elapsed_time_label = QLabel("耗时: ")
        self.elapsed_time_label.setStyleSheet("font-size: 11pt;")
        left_layout.addWidget(self.elapsed_time_label)
        
        # 日志输出区
        log_label = QLabel("运行日志:")
        log_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        left_layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 10pt;
                background-color: #f8f8f8;
                border: 1px solid #cccccc;
            }
        """)
        self.log_output.setMinimumHeight(150)  # 增加日志区域高度
        left_layout.addWidget(self.log_output)
        
        content_splitter.addWidget(left_widget)
        
        # 右侧区域（问答展示）
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        
        # 问答表格
        qa_label = QLabel("问答结果:")
        qa_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        right_layout.addWidget(qa_label)
        
        self.qa_table = QTableWidget()
        self.qa_table.setColumnCount(4)
        self.qa_table.setHorizontalHeaderLabels(["序号", "问题", "答案", "耗时(秒)"])
        self.qa_table.setStyleSheet("""
            QTableWidget {
                font-size: 11pt;
                gridline-color: #d0d0d0;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                font-size: 11pt;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #cccccc;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        # 设置表格样式
        header = self.qa_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 序号列自适应
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # 问题列可调整
        header.setSectionResizeMode(2, QHeaderView.Interactive)  # 答案列可调整
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 耗时列自适应
        
        # 设置默认列宽
        self.qa_table.setColumnWidth(1, 400)  # 问题列宽
        self.qa_table.setColumnWidth(2, 600)  # 答案列宽
        
        # 允许自动换行
        self.qa_table.setWordWrap(True)
        
        # 设置选择模式
        self.qa_table.setSelectionMode(QTableWidget.SingleSelection)
        self.qa_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        right_layout.addWidget(self.qa_table)
        
        # 汇总信息
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("""
            QLabel {
                font-size: 12pt;
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        right_layout.addWidget(self.summary_label)
        
        # 在汇总信息下方添加下载按钮
        self.download_button = QPushButton("导出到Excel")
        self.download_button.setStyleSheet("""
            QPushButton {
                font-size: 12pt;
                padding: 8px;
                min-width: 120px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.download_button.clicked.connect(self.export_to_excel)
        self.download_button.setEnabled(False)  # 初始状态禁用
        right_layout.addWidget(self.download_button)
        
        content_splitter.addWidget(right_widget)
        
        # 设置分割器的初始大小比例（左:右 = 35:65）
        content_splitter.setSizes([560, 1040])
        
        main_layout.addWidget(content_splitter)
        
        # 设置初始状态
        self.progress_bar.setValue(0)
        self.qa_table.setRowCount(0)

    def append_log(self, message):
        """添加日志到日志输出区"""
        self.log_output.append(message)
        # 滚动到底部
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_qa_pair(self, index, question, response, elapsed_time):
        """添加一条问答记录到表格"""
        # 保存结果用于导出
        result = {
            "序号": index + 1,
            "问题": question,
            "答案": response.get("answer", f"错误: {response.get('error', '未知错误')}"),
            "耗时(秒)": f"{elapsed_time:.2f}"
        }
        self.qa_results.append(result)
        
        row = self.qa_table.rowCount()
        self.qa_table.insertRow(row)
        
        # 序号
        index_item = QTableWidgetItem(str(index + 1))
        index_item.setTextAlignment(Qt.AlignCenter)
        self.qa_table.setItem(row, 0, index_item)
        
        # 问题
        question_item = QTableWidgetItem(question)
        question_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.qa_table.setItem(row, 1, question_item)
        
        # 答案 - 使用QTextEdit作为单元格组件
        answer_widget = QTextEdit()
        answer_widget.setReadOnly(True)
        answer_widget.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: transparent;
                font-size: 11pt;
            }
        """)
        
        if "error" in response:
            answer_text = f"错误: {response['error']}"
            answer_widget.setStyleSheet(answer_widget.styleSheet() + "color: red;")
        else:
            answer_text = response["answer"]
        
        # 设置答案文本
        answer_widget.setText(answer_text)
        
        # 计算所需的最小高度
        document = answer_widget.document()
        document.setTextWidth(self.qa_table.columnWidth(2) - 20)  # 减去一些边距
        doc_height = document.size().height()
        row_height = int(max(doc_height + 20, 60))  # 将浮点数转换为整数
        
        # 设置行高
        self.qa_table.setRowHeight(row, row_height)
        
        # 将QTextEdit添加到表格
        self.qa_table.setCellWidget(row, 2, answer_widget)
        
        # 耗时
        time_item = QTableWidgetItem(f"{elapsed_time:.2f}")
        time_item.setTextAlignment(Qt.AlignCenter)
        self.qa_table.setItem(row, 3, time_item)
        
        # 自动滚动到最新行
        self.qa_table.scrollToBottom()

    def export_to_excel(self):
        """导出问答结果到Excel文件"""
        try:
            # 获取保存文件路径
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"问答测试结果_{current_time}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存Excel文件",
                default_filename,
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:  # 用户取消了保存
                return
                
            # 如果用户没有输入.xlsx后缀，自动添加
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            
            # 创建DataFrame并保存为Excel
            df = pd.DataFrame(self.qa_results)
            
            # 设置Excel写入选项
            writer = pd.ExcelWriter(file_path, engine='openpyxl')
            df.to_excel(writer, index=False, sheet_name='测试结果')
            
            # 调整列宽和格式
            workbook = writer.book
            worksheet = writer.sheets['测试结果']
            
            # 设置列宽
            worksheet.column_dimensions['A'].width = 8   # 序号
            worksheet.column_dimensions['B'].width = 40  # 问题
            worksheet.column_dimensions['C'].width = 60  # 答案
            worksheet.column_dimensions['D'].width = 12  # 耗时
            
            # 设置自动换行和对齐方式
            from openpyxl.styles import Alignment, Border, Side
            wrap_alignment = Alignment(wrap_text=True, vertical='top')
            no_border = Border(left=Side(style=None), 
                             right=Side(style=None),
                             top=Side(style=None),
                             bottom=Side(style=None))
            
            # 为所有单元格设置格式
            for row in worksheet.iter_rows():
                for cell in row:
                    cell.border = no_border
                    if row[0].row == 1:  # 表头行
                        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    else:  # 数据行
                        cell.alignment = wrap_alignment
                        # 为序号和耗时列设置居中对齐
                        if cell.column_letter in ['A', 'D']:
                            cell.alignment = Alignment(horizontal='center', vertical='top')
            
            # 保存文件
            writer.close()
            
            QMessageBox.information(
                self,
                "导出成功",
                f"结果已成功导出到：\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "导出失败",
                f"导出Excel文件时发生错误：\n{str(e)}"
            )

    def start_testing(self):
        # 获取问题列表
        questions_text = self.questions_input.toPlainText().strip()
        if not questions_text:
            self.status_label.setText("错误: 问题列表为空")
            return
        
        questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
        
        # 获取设置
        base_url = self.base_url_input.text().strip()
        token = self.token_input.text().strip()
        agent_id = self.agent_id_input.text().strip()
        
        # 初始化界面
        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("测试中...")
        self.log_output.clear()
        self.qa_table.setRowCount(0)
        self.current_question_label.setText("当前问题: ")
        self.elapsed_time_label.setText("耗时: ")
        self.summary_label.setText("")
        
        # 清空之前的结果
        self.qa_results = []
        self.download_button.setEnabled(False)
        
        # 创建并启动工作线程
        self.worker = RequestWorker(questions, base_url, token, agent_id)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.complete.connect(self.testing_complete)
        self.worker.log_message.connect(self.append_log)
        self.worker.start()

    def update_progress(self, percentage, current_question, elapsed_time):
        self.progress_bar.setValue(percentage)
        self.current_question_label.setText(f"当前问题: {current_question}")
        self.elapsed_time_label.setText(f"耗时: {elapsed_time:.2f} 秒")
        
        # 获取当前问答对的索引
        current_index = self.qa_table.rowCount()
        
        # 添加到问答表格
        self.add_qa_pair(
            current_index,
            current_question,
            self.worker.results[current_index]["response"],
            elapsed_time
        )

    def testing_complete(self, results):
        self.status_label.setText("测试完成")
        self.run_button.setEnabled(True)
        
        # 计算并显示汇总信息
        total_time = sum(result['time'] for result in results)
        avg_time = total_time / len(results) if results else 0
        error_count = sum(1 for result in results if 'error' in result['response'])
        
        summary_text = (
            f"测试完成！\n"
            f"总问题数: {len(results)} | "
            f"成功: {len(results) - error_count} | "
            f"失败: {error_count}\n"
            f"总耗时: {total_time:.2f}秒 | "
            f"平均耗时: {avg_time:.2f}秒"
        )
        self.summary_label.setText(summary_text)
        
        # 启用下载按钮
        self.download_button.setEnabled(True)


if __name__ == "__main__":
    # 设置控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().setLevel(logging.INFO)
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 