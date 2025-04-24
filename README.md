# 问题批量测试工具

一个使用PyQt5开发的图形界面工具，用于批量发送问题到HTTP接口并收集响应结果。

## 功能特点

- 支持输入多行问题列表
- 可配置基础URL、Token和Agent ID
- 显示请求进度条和执行时间
- 汇总测试结果
- 支持模拟或真实HTTP请求模式

## 环境要求

- Python 3.6+
- PyQt5
- requests
- Flask (用于模拟服务器)

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方法

### 启动主应用程序

```bash
python main.py
```

### 启动模拟服务器（可选）

如果需要测试实际HTTP请求，可以启动模拟服务器：

```bash
python mock_server.py
```

服务器将在 http://localhost:8000 启动。

## 使用说明

1. 在界面上输入Base URL、Token和Agent ID
   - 如果使用模拟服务器，默认URL为 http://localhost:8000
   - 任意输入一个Token格式如: test_token_123
   - 任意输入Agent ID
2. 选择使用模拟模式或实际HTTP请求模式
3. 在问题列表文本框中输入要测试的问题，每行一个
4. 点击"开始测试"按钮
5. 查看测试进度和结果

## 项目结构

- `main.py` - 主应用程序
- `api_client.py` - API客户端实现
- `mock_server.py` - 模拟服务器
- `requirements.txt` - 依赖项列表

## 注意事项

- 当使用模拟模式时，请求不会真正发送到服务器
- 当使用实际HTTP请求模式时，请确保服务器正在运行，或者修改API客户端以连接到实际后端 


## 打包为 exe 文件
python -m PyInstaller --clean main.spec