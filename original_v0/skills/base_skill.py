# -*- coding: utf-8 -*-
"""Skill 基类定义"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import yaml
import os


class BaseSkill(ABC):
    """所有 Skill 的基类
    
    每个 Skill 需要实现：
    1. can_handle(): 判断是否能处理当前上下文
    2. execute(): 执行 Skill 逻辑
    3. SKILL.md 元数据文件（可选，用于描述和配置）
    """
    
    def __init__(self, skill_dir: Optional[str] = None):
        """初始化 Skill
        
        Args:
            skill_dir: Skill 所在目录路径，用于加载 SKILL.md 和其他资源
        """
        self.skill_dir = skill_dir
        self.metadata = self._load_metadata() if skill_dir else {}
        self.name = self.metadata.get("name", self.__class__.__name__)
        self.version = self.metadata.get("version", "0.0.0")
        self.description = self.metadata.get("description", "")
        self.triggers = self.metadata.get("triggers", {})
        self.capabilities = self.metadata.get("capabilities", [])
        self.priority = int(self.metadata.get("priority", getattr(self, "PRIORITY", 0)))
    
    def _load_metadata(self) -> Dict[str, Any]:
        """从 SKILL.md 加载元数据（YAML frontmatter）"""
        skill_md = os.path.join(self.skill_dir, "SKILL.md")
        if not os.path.exists(skill_md):
            return {}
        
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取 YAML frontmatter（--- ... ---）
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    return {}
        return {}
    
    @abstractmethod
    def can_handle(self, context: Dict[str, Any]) -> bool:
        """判断是否能处理当前上下文
        
        Args:
            context: 上下文信息，包括：
                - user_input: 用户输入
                - history: 对话历史
                - agent_state: Agent 状态
                - 其他自定义字段
        
        Returns:
            True 表示可以处理，False 表示不能处理
        """
        pass
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Skill 逻辑
        
        Args:
            context: 上下文信息
        
        Returns:
            执行结果字典，包括：
                - handled: bool，是否成功处理
                - response: str，返回给用户的文本
                - data: Any，额外的数据（可选）
                - error: str，错误信息（可选）
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """返回 Skill 元数据"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities,
            "triggers": self.triggers,
            "priority": self.priority,
        }
    
    def _match_keywords(self, text: str, keywords: List[str]) -> bool:
        """辅助方法：检查文本是否包含任一关键词"""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)
