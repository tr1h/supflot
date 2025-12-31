"""Оркестратор для управления агентами"""
import logging
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """Оркестратор для управления агентами и распределения задач"""
    
    def __init__(self):
        """Инициализация оркестратора с агентами"""
        self.logger = logging.getLogger("orchestrator")
        self.agents: Dict[str, BaseAgent] = {}
        self.initialize_agents()
    
    def initialize_agents(self):
        """Инициализация всех агентов"""
        # Ленивая инициализация для избежания циклических импортов
        from agents.planning_agent import PlanningAgent
        from agents.development_agent import DevelopmentAgent
        from agents.documentation_agent import DocumentationAgent
        from agents.testing_agent import TestingAgent
        
        self.agents["planning"] = PlanningAgent()
        self.agents["development"] = DevelopmentAgent()
        self.agents["documentation"] = DocumentationAgent()
        self.agents["testing"] = TestingAgent()
        self.logger.info(f"Initialized {len(self.agents)} agents")
    
    async def execute_task(
        self,
        task: str,
        task_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Выполнение задачи через соответствующий агент
        
        Args:
            task: Описание задачи
            task_type: Тип задачи (planning, development, documentation, testing, auto)
            context: Дополнительный контекст
        
        Returns:
            Результат выполнения задачи
        """
        # Если тип не указан, определяем автоматически
        if not task_type or task_type == "auto":
            task_type = self._detect_task_type(task)
        
        # Выбираем агента
        agent = self.agents.get(task_type)
        if not agent:
            return {
                "success": False,
                "error": f"Unknown task type: {task_type}",
                "available_types": list(self.agents.keys())
            }
        
        self.logger.info(f"Executing task '{task[:50]}...' with agent: {task_type}")
        
        # Выполняем задачу
        result = await agent.execute(task, context)
        
        return {
            **result,
            "task_type": task_type,
            "agent_used": task_type
        }
    
    def _detect_task_type(self, task: str) -> str:
        """
        Автоматическое определение типа задачи по тексту
        
        Args:
            task: Описание задачи
        
        Returns:
            Тип задачи
        """
        task_lower = task.lower()
        
        # Планирование
        planning_keywords = [
            "план", "планирование", "roadmap", "задачи", "приоритет",
            "что делать", "что реализовать", "features", "features"
        ]
        if any(keyword in task_lower for keyword in planning_keywords):
            return "planning"
        
        # Тестирование
        testing_keywords = [
            "тест", "test", "проверка", "проверить", "баг", "bug",
            "ошибка", "error", "исправить", "fix", "валидация"
        ]
        if any(keyword in task_lower for keyword in testing_keywords):
            return "testing"
        
        # Документация
        documentation_keywords = [
            "документ", "documentation", "readme", "описать", "описание",
            "комментарий", "comment", "документировать", "инструкция"
        ]
        if any(keyword in task_lower for keyword in documentation_keywords):
            return "documentation"
        
        # Разработка (по умолчанию)
        return "development"
    
    async def execute_pipeline(
        self,
        tasks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполнение последовательности задач (пайплайн)
        
        Args:
            tasks: Список задач с указанием типа
            context: Общий контекст для всех задач
        
        Returns:
            Список результатов выполнения задач
        """
        results = []
        shared_context = context.copy() if context else {}
        
        for i, task_data in enumerate(tasks):
            task = task_data.get("task", "")
            task_type = task_data.get("type", "auto")
            task_context = task_data.get("context", {})
            
            # Объединяем контексты
            combined_context = {**shared_context, **task_context}
            
            self.logger.info(f"Pipeline step {i+1}/{len(tasks)}: {task_type}")
            
            result = await self.execute_task(task, task_type, combined_context)
            results.append(result)
            
            # Если задача провалилась, можно прервать пайплайн
            if not result.get("success") and task_data.get("required", True):
                self.logger.warning(f"Pipeline stopped at step {i+1} due to failure")
                break
            
            # Добавляем результат в общий контекст для следующих задач
            if result.get("success"):
                shared_context[f"step_{i}_result"] = result.get("result")
        
        return results
    
    async def plan_and_execute(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Планирование и выполнение задачи
        
        Args:
            goal: Цель/задача
            context: Контекст
        
        Returns:
            Результат выполнения
        """
        # Шаг 1: Планирование
        planning_result = await self.execute_task(
            f"Создай план для достижения цели: {goal}",
            "planning",
            context
        )
        
        if not planning_result.get("success"):
            return planning_result
        
        # Шаг 2: Выполнение плана
        plan = planning_result.get("result", "")
        
        execution_result = await self.execute_task(
            f"Выполни следующую задачу согласно плану:\n\n{plan}\n\nЦель: {goal}",
            "development",
            {**(context or {}), "plan": plan}
        )
        
        return {
            "success": execution_result.get("success", False),
            "plan": plan,
            "execution": execution_result
        }
    
    def get_agents_info(self) -> Dict[str, Any]:
        """Получение информации об агентах"""
        return {
            agent_name: {
                "name": agent.name,
                "role": agent.role,
                "enabled": agent.ai_service.enabled
            }
            for agent_name, agent in self.agents.items()
        }
    
    async def review_code(
        self,
        code: str,
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Код-ревью через нескольких агентов
        
        Args:
            code: Код для ревью
            focus: Область фокуса (security, performance, style, etc.)
        
        Returns:
            Результаты ревью от разных агентов
        """
        context = {"code": code, "focus": focus}
        
        # Получаем мнения от разных агентов
        reviews = {}
        
        # Development agent - общий обзор
        dev_result = await self.execute_task(
            f"Проведи код-ревью с фокусом на {focus or 'качество кода'}",
            "development",
            context
        )
        reviews["development"] = dev_result
        
        # Testing agent - проверка на баги
        test_result = await self.execute_task(
            "Найди потенциальные баги и проблемы",
            "testing",
            context
        )
        reviews["testing"] = test_result
        
        return {
            "success": True,
            "code": code,
            "reviews": reviews
        }


# Глобальный экземпляр оркестратора
_orchestrator_instance: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Получение глобального экземпляра оркестратора"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance

