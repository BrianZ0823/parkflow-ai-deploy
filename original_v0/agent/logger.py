# -*- coding: utf-8 -*-
"""
对话日志记录器
记录用户输入、Agent 思考、工具调用、工具返回及最终回复
"""
import os
import datetime
import json
import logging

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
logger = logging.getLogger(__name__)


class ConversationLogger:
    def __init__(self):
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        # 每次启动创建一个新的日志文件，文件名包含时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(LOG_DIR, f"conversation_{timestamp}.log")
        
        # 写入文件头
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"=== Conversation Log Started at {timestamp} ===\n\n")
        
        logger.info("日志已开启: %s", self.log_file)

    def log_section(self, role, content, meta=None):
        """通用日志写入函数"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        with open(self.log_file, "a", encoding="utf-8", errors='replace') as f:
            f.write(f"[{timestamp}] [{role.upper()}]\n")
            
            if meta:
                f.write(f"Meta: {json.dumps(meta, ensure_ascii=False)}\n")
            
            if isinstance(content, (dict, list)):
                f.write(json.dumps(content, indent=2, ensure_ascii=False))
            else:
                f.write(str(content))
            
            f.write("\n\n" + "-"*40 + "\n\n")

    def log_system_prompt(self, content):
        self.log_section("SYSTEM_PROMPT", content)

    def log_request_payload(self, messages):
        """记录发送给 LLM 的完整消息列表 (Context)"""
        self.log_section("LLM_REQUEST_CONTEXT", messages)

    def log_user_input(self, input_text):
        self.log_section("USER", input_text)

    def log_agent_response(self, text, tool_calls=None, metadata=None):
        meta = {}
        if tool_calls:
            meta["tool_calls"] = tool_calls
        if metadata:
            meta.update(metadata)
        if meta:
            self.log_section("AGENT_THOUGHT_ACTION", text or "(No content, triggering tools)", meta=meta)
        else:
            self.log_section("AGENT_RESPONSE", text)

    def log_tool_execution(self, tool_name, args, result):
        self.log_section("TOOL_EXECUTION", result, meta={"tool": tool_name, "args": args})

    def log_error(self, error):
        self.log_section("ERROR", str(error))
