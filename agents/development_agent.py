"""Агент разработки"""
from agents.base_agent import BaseAgent
from typing import Optional


class DevelopmentAgent(BaseAgent):
    """Агент для разработки кода и реализации функций"""
    
    def __init__(self):
        system_prompt = """Ты опытный Python разработчик, специализирующийся на:
- Telegram ботах (aiogram)
- Асинхронном программировании (asyncio)
- Работе с базами данных (SQLite, aiosqlite)
- Архитектуре сервисов и обработчиков

Твоя задача - писать чистый, понятный, эффективный код, следующий лучшим практикам Python.

Требования к коду:
1. Используй type hints
2. Добавляй docstrings
3. Следуй PEP 8
4. Обрабатывай ошибки (try-except)
5. Используй async/await где необходимо
6. Логируй важные события
7. Пиши код на русском (комментарии, docstrings, строки для пользователей)

Отвечай на русском языке. Код должен быть готов к использованию."""
        
        super().__init__(
            name="DevelopmentAgent",
            role="Разработчик",
            system_prompt=system_prompt
        )
    
    def _get_task_instructions(self) -> str:
        return """Реализуй задачу, предоставив:
1. Полный код с импортами
2. Объяснение логики
3. Пример использования (если применимо)
4. Рекомендации по интеграции

Код должен быть готов к копированию и использованию."""
    
    async def implement_feature(
        self,
        feature_description: str,
        context: Optional[dict] = None
    ) -> dict:
        """
        Реализация функции
        
        Args:
            feature_description: Описание функции
            context: Контекст (существующий код, структура проекта)
        
        Returns:
            Реализация функции
        """
        task = f"Реализуй следующую функцию: {feature_description}"
        return await self.execute(task, context)
    
    async def refactor_code(
        self,
        code: str,
        goal: str = "улучшить качество кода"
    ) -> dict:
        """
        Рефакторинг кода
        
        Args:
            code: Код для рефакторинга
            goal: Цель рефакторинга
        
        Returns:
            Отрефакторенный код
        """
        task = f"Отрефакторь код с целью: {goal}"
        context = {"code": code, "goal": goal}
        return await self.execute(task, context)
    
    async def fix_bug(
        self,
        code: str,
        bug_description: str,
        error_message: Optional[str] = None
    ) -> dict:
        """
        Исправление бага
        
        Args:
            code: Код с багом
            bug_description: Описание проблемы
            error_message: Сообщение об ошибке (если есть)
        
        Returns:
            Исправленный код
        """
        task = f"Исправь баг: {bug_description}"
        if error_message:
            task += f"\n\nОшибка: {error_message}"
        
        context = {"code": code, "bug": bug_description}
        return await self.execute(task, context)
    
    async def write_function(
        self,
        function_signature: str,
        requirements: str,
        context: Optional[dict] = None
    ) -> dict:
        """
        Написание функции по сигнатуре и требованиям
        
        Args:
            function_signature: Сигнатура функции
            requirements: Требования к функции
            context: Контекст (другие функции, структура)
        
        Returns:
            Реализация функции
        """
        task = f"Напиши функцию:\n{function_signature}\n\nТребования: {requirements}"
        return await self.execute(task, context)

