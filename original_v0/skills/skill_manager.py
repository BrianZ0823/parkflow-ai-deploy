# -*- coding: utf-8 -*-
"""Skill 管理器 - 负责加载、注册和匹配 Skills"""
from typing import Dict, Any, List, Type
import os
import sys
import importlib.util
import logging
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class SkillManager:
    """管理所有 Skills 的加载、注册和调用"""
    
    def __init__(self, builtin_skills_dir: str = None, global_skills_dir: str = None):
        """初始化 Skill 管理器
        
        Args:
            builtin_skills_dir: 内置 Skills 目录路径
            global_skills_dir: 全局 Skills 目录路径（Antigravity 系统级）
        """
        self.skills: List[BaseSkill] = []
        self.builtin_skills_dir = builtin_skills_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "skills", "builtin"
        )
        self.global_skills_dir = global_skills_dir
    
    def load_builtin_skills(self):
        """加载内置 Skills"""
        if not os.path.exists(self.builtin_skills_dir):
            logger.warning("[SkillManager] 内置 Skills 目录不存在: %s", self.builtin_skills_dir)
            return
        
        for skill_name in os.listdir(self.builtin_skills_dir):
            skill_dir = os.path.join(self.builtin_skills_dir, skill_name)
            if not os.path.isdir(skill_dir):
                continue
            
            # 查找 skill.py 文件
            skill_file = os.path.join(skill_dir, "skill.py")
            if not os.path.exists(skill_file):
                logger.debug("[SkillManager] 跳过 %s（缺少 skill.py）", skill_name)
                continue
            
            try:
                # 动态加载 skill.py 模块
                spec = importlib.util.spec_from_file_location(
                    f"skills.builtin.{skill_name}", skill_file
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                
                # 查找 BaseSkill 的子类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, BaseSkill) and 
                        attr is not BaseSkill):
                        # 实例化并注册
                        skill_instance = attr(skill_dir=skill_dir)
                        self.register_skill(skill_instance)
                        logger.info("[SkillManager] 已加载 Skill: %s", skill_instance.name)
                        break
            except Exception as e:
                logger.exception("[SkillManager] 加载 %s 失败: %s", skill_name, e)
    
    def load_global_skills(self):
        """加载全局 Skills（Antigravity 系统级）
        
        全局 Skills 位于 Antigravity 的 skills 目录，
        可以被所有项目共享使用。
        """
        if not self.global_skills_dir or not os.path.exists(self.global_skills_dir):
            # 尝试自动检测 Antigravity skills 目录
            antigravity_skills = os.path.expanduser(
                r"~\.gemini\antigravity\skills"
            )
            if os.path.exists(antigravity_skills):
                self.global_skills_dir = antigravity_skills
            else:
                logger.debug("[SkillManager] 未找到全局 Skills 目录")
                return
        
        logger.info("[SkillManager] 扫描全局 Skills: %s", self.global_skills_dir)
        
        # 这里可以实现全局 Skills 的加载逻辑
        # 由于全局 Skills 的格式可能不同，这里暂时预留接口
        # 后续可以根据 Antigravity 的实际格式进行适配
        logger.info("[SkillManager] 全局 Skills 加载功能待实现")
    
    def register_skill(self, skill: BaseSkill):
        """注册一个 Skill 实例"""
        self.skills.append(skill)
    
    def find_matching_skills(self, context: Dict[str, Any]) -> List[BaseSkill]:
        """查找能处理当前上下文的 Skills
        
        Args:
            context: 上下文信息
        
        Returns:
            匹配的 Skills 列表，按优先级排序
        """
        matching = []
        for skill in self.skills:
            try:
                if skill.can_handle(context):
                    matching.append(skill)
            except Exception as e:
                logger.exception("[SkillManager] %s can_handle() 出错: %s", skill.name, e)
        
        # 这里可以实现优先级排序逻辑
        # 暂时按注册顺序返回
        matching.sort(key=lambda skill: getattr(skill, "priority", 0), reverse=True)
        return matching
    
    def get_all_skills(self) -> List[Dict[str, Any]]:
        """获取所有已注册 Skills 的元数据"""
        return [skill.get_metadata() for skill in self.skills]
    
    def get_skill_by_name(self, name: str) -> BaseSkill:
        """根据名称获取 Skill"""
        for skill in self.skills:
            if skill.name == name:
                return skill
        return None
