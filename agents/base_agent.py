"""Базовый класс для агентов"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from services.ai_service import get_ai_service

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Базовый класс для всех агентов"""
    
    def __init__(self, name: str, role: str, system_prompt: str):
        """
        Инициализация агента
        
        Args:
            name: Имя агента
            role: Роль агента (для промптов)
            system_prompt: Системный промпт, определяющий поведение агента
        """
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.ai_service = get_ai_service()
        self.logger = logging.getLogger(f"agent.{name}")
    
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнение задачи агентом
        
        Args:
            task: Описание задачи
            context: Дополнительный контекст (код, файлы, история и т.д.)
        
        Returns:
            Результат выполнения задачи
        """
        self.logger.info(f"Agent {self.name} executing task: {task[:100]}")
        
        try:
            # Формируем промпт с контекстом
            prompt = self._build_prompt(task, context)
            
            # Вызываем AI сервис
            result = await self.ai_service._call_opencode(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            if not result:
                return {
                    "success": False,
                    "error": "AI service returned no result",
                    "agent": self.name
                }
            
            # Парсим результат
            parsed_result = self._parse_result(result, context)
            
            return {
                "success": True,
                "result": parsed_result,
                "raw_output": result,
                "agent": self.name
            }
            
        except Exception as e:
            self.logger.error(f"Error executing task in {self.name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _build_prompt(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Построение промпта для задачи
        
        Args:
            task: Описание задачи
            context: Дополнительный контекст
        
        Returns:
            Сформированный промпт
        """
        prompt = f"Задача: {task}\n\n"
        
        if context:
            if "code" in context:
                prompt += f"Код для анализа:\n```\n{context['code']}\n```\n\n"
            if "files" in context:
                prompt += f"Файлы: {', '.join(context['files'])}\n\n"
            if "history" in context:
                prompt += f"История:\n{context['history']}\n\n"
            if "requirements" in context:
                prompt += f"Требования:\n{context['requirements']}\n\n"
        
        prompt += self._get_task_instructions()
        
        return prompt
    
    def _parse_result(self, result: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Парсинг результата от AI
        
        Args:
            result: Сырой результат от AI
            context: Контекст задачи
        
        Returns:
            Распарсенный результат
        """
        # Базовая реализация - просто возвращаем результат
        # Каждый агент может переопределить этот метод для специфичной обработки
        return result.strip()
    
    @abstractmethod
    def _get_task_instructions(self) -> str:
        """
        Получение инструкций для конкретного типа задач
        
        Returns:
            Строка с инструкциями
        """
        pass
    
    async def analyze(self, content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        Анализ контента
        
        Args:
            content: Контент для анализа
            analysis_type: Тип анализа
        
        Returns:
            Результат анализа
        """
        task = f"Проанализируй следующий {analysis_type}:"
        context = {"code" if analysis_type in ["code", "function", "class"] else "content": content}
        return await self.execute(task, context)
    
    async def suggest_improvements(self, content: str, focus: str = "general") -> Dict[str, Any]:
        """
        Предложение улучшений
        
        Args:
            content: Контент для улучшения
            focus: Область фокуса (performance, readability, security и т.д.)
        
        Returns:
            Предложения по улучшению
        """
        task = f"Предложи улучшения с фокусом на {focus}:"
        context = {"content": content, "focus": focus}
        return await self.execute(task, context)

