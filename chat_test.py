"""
使用方法：
1. 安装依赖:
   pip install requests==2.31.0 aiohttp==3.9.1 asyncio==3.4.3

2. 运行测试:
   python chat_test.py
"""

import requests
import json
import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List, Dict, Tuple
import os
import logging

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ChatTester:
    def __init__(self, url: str, token: str):
        self.url = url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        logger.info(f"初始化ChatTester，目标URL: {url}")
        
    async def async_chat_once(self, session: aiohttp.ClientSession, messages: List[Dict]) -> Tuple[str, str, float]:
        """
        异步单次对话函数
        :param session: aiohttp session
        :param messages: 消息列表
        :return: (原始问题, 模型回答, 请求耗时)
        """
        question = messages[-1]['content']
        logger.info(f"发送异步请求，问题: {question}")
        
        payload = {
            "model": "model",
            "messages": messages,
            "stream": False
        }
        
        try:
            start_time = time.time()
            async with session.post(self.url, headers=self.headers, json=payload) as response:
                result = await response.json()
                answer = result['choices'][0]['message']['content']
                elapsed = time.time() - start_time
                
                logger.info("-" * 25 + " 一个请求完成：开始打印 " + "-" * 25)
                logger.info(f"\n\n请求完成，耗时: {elapsed:.2f}秒")
                logger.info(f"问题: {question}")
                logger.info(f"回答: {answer[:200]}...\n\n")
                logger.info("-" * 25 + " 一个请求完成：结束打印 " + "-" * 25)
                return question, answer, elapsed
        except Exception as e:
            logger.error(f"异步请求失败: {str(e)}")
            return question, f"Error: {str(e)}", 0.0

    def _prepare_test_directory(self, questions: List[str]) -> Tuple[str, str, str]:
        """
        准备测试目录和文件
        :param questions: 问题列表
        :return: (时间戳, 结果目录路径, 结果文件路径)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = f"test_results_{timestamp}"
        result_file = f"{result_dir}/results.txt"
        
        # 创建目录
        os.makedirs(result_dir, exist_ok=True)
        logger.info(f"创建结果目录: {result_dir}")
        
        # 保存问题列表
        with open(f"{result_dir}/questions.txt", "w", encoding='utf-8') as f:
            for q in questions:
                f.write(f"{q}\n")
        logger.info("已保存问题列表")
        
        return timestamp, result_dir, result_file

    def _prepare_messages(self, questions: List[str]) -> List[List[Dict]]:
        """
        准备消息列表
        :param questions: 问题列表
        :return: 处理后的消息列表
        """
        return [[{"role": "user", "content": q}] for q in questions]

    async def _execute_concurrent_requests(
        self, 
        session: aiohttp.ClientSession,
        all_messages: List[List[Dict]], 
        concurrency: int
    ) -> Tuple[List[Tuple[str, str, float]], float]:
        """
        执行并发请求
        :param session: aiohttp会话
        :param all_messages: 所有消息
        :param concurrency: 并发数
        :return: (结果列表, 总耗时)
        """
        completed_count = 0
        sem = asyncio.Semaphore(concurrency)
        logger.info("创建信号量，准备执行并发请求")
        
        async def controlled_chat(messages):
            nonlocal completed_count
            async with sem:
                result = await self.async_chat_once(session, messages)
                completed_count += 1
                logger.info(f"进度: {completed_count}/{len(all_messages)} ({(completed_count/len(all_messages)*100):.1f}%)")
                return result
        
        tasks = [controlled_chat(msgs) for msgs in all_messages]
        logger.info("已创建所有任务")
        
        start_time = time.time()
        logger.info("开始执行并发请求...")
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        logger.info(f"所有请求完成，总耗时: {total_time:.2f}秒")
        logger.info(f"平均每个请求耗时: {total_time/len(all_messages):.2f}秒")
        
        return results, total_time

    def _save_results(
        self, 
        result_file: str,
        timestamp: str,
        results: List[Tuple[str, str, float]],
        total_time: float,
        questions_count: int,
        concurrency: int
    ):
        """
        保存测试结果
        :param result_file: 结果文件路径
        :param timestamp: 时间戳
        :param results: 结果列表 (问题, 回答, 耗时)
        :param total_time: 总耗时
        :param questions_count: 问题总数
        :param concurrency: 并发数
        """
        with open(result_file, "w", encoding='utf-8') as f:
            # 写入测试信息
            f.write(f"测试时间: {timestamp}\n")
            f.write(f"总问题数: {questions_count}\n")
            f.write(f"并发数: {concurrency}\n")
            f.write(f"总耗时: {total_time:.2f}秒\n")
            f.write(f"平均耗时: {total_time/questions_count:.2f}秒\n\n")
            
            # 写入问答结果
            for question, answer, elapsed in results:
                f.write(f"问题: {question}\n")
                f.write(f"耗时: {elapsed:.2f}秒\n")
                f.write(f"回答: {answer}\n")
                f.write("\n" + "-" * 50 + "\n\n")
            
            # 写入耗时统计
            f.write("\n=== 耗时统计 ===\n")
            sorted_results = sorted(results, key=lambda x: x[2], reverse=True)
            f.write("\n按耗时降序排列的问题：\n")
            for question, _, elapsed in sorted_results:
                f.write(f"{elapsed:.2f}秒: {question}\n")
        
        logger.info(f"测试结果已保存到: {result_file}")

    async def run_concurrent_tests(self, questions: List[str], concurrency: int = 5):
        """
        运行并发测试
        :param questions: 问题列表
        :param concurrency: 并发数
        """
        logger.info(f"开始并发测试，问题数量: {len(questions)}，并发数: {concurrency}")
        
        # 准备测试环境
        timestamp, result_dir, result_file = self._prepare_test_directory(questions)
        all_messages = self._prepare_messages(questions)
        
        # 执行并发请求
        async with aiohttp.ClientSession() as session:
            results, total_time = await self._execute_concurrent_requests(
                session, all_messages, concurrency
            )
            
            # 保存结果
            self._save_results(
                result_file,
                timestamp,
                results,
                total_time,
                len(questions),
                concurrency
            )
        
        logger.info("测试完成！")

def main():
    # 配置参数
    url = "https://ragflow-bmhagent.wasumedia.cn/api/v1/w_agents_openai/9e6a7dbe1b2b11f08f630242c0a87006/chat/completions"
    token = "ragflow-MyNTY5YWE0MWIzMDExZjBhOTY2MDI0Mm"
    
    logger.info("程序启动")
    
    # 测试问题列表
    questions = [
        "景区在哪里？",
        "怎么买票",
        "黄龙洞介绍一下",
        "需要预约吗",
        "西湖在哪里",
        "有停车场吗",
        "横店在哪里",
        "可以带宠物吗",
        "绍兴景点有哪些",
        "有导游吗",
        "可以带食物进去吗",
        "有餐厅吗",
    ]
    
    # 创建测试器实例
    tester = ChatTester(url, token)
    
    # 运行并发测试
    logger.info("开始运行测试...")
    asyncio.run(tester.run_concurrent_tests(questions, concurrency=1))
    logger.info("程序结束")

if __name__ == "__main__":
    main() 