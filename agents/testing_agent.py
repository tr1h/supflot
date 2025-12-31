"""Агент тестирования"""
from agents.base_agent import BaseAgent
from typing import Optional


class TestingAgent(BaseAgent):
    """Агент для написания тестов и поиска багов"""
    
    def __init__(self):
        system_prompt = """Ты эксперт по тестированию ПО.
Твоя задача - создавать качественные тесты и находить потенциальные проблемы в коде.

Требования к тестам:
1. Использование pytest
2. Покрытие основных сценариев
3. Тестирование граничных случаев
4. Моки для внешних зависимостей
5. Понятные имена тестов
6. Assertions с понятными сообщениями

Требования к анализу кода:
1. Поиск потенциальных багов
2. Проверка обработки ошибок
3. Проверка edge cases
4. Оценка безопасности

Отвечай на русском языке. Тесты должны быть надежными и поддерживаемыми."""
        
        super().__init__(
            name="TestingAgent",
            role="Тестировщик",
            system_prompt=system_prompt
        )
    
    def _get_task_instructions(self) -> str:
        return """Создай тесты или проанализируй код, включив:
1. Тесты для основных сценариев
2. Тесты для граничных случаев
3. Моки для зависимостей (если нужны)
4. Понятные имена тестов
5. Описания того, что тестируется"""
    
    async def write_tests(
        self,
        code: str,
        test_type: str = "unit",
        framework: str = "pytest"
    ) -> dict:
        """
        Написание тестов для кода
        
        Args:
            code: Код для тестирования
            test_type: Тип тестов (unit, integration, e2e)
            framework: Фреймворк (pytest)
        
        Returns:
            Код тестов
        """
        task = f"Напиши {test_type} тесты используя {framework} для следующего кода:"
        context = {"code": code, "test_type": test_type, "framework": framework}
        return await self.execute(task, context)
    
    async def find_bugs(
        self,
        code: str,
        focus: Optional[str] = None
    ) -> dict:
        """
        Поиск багов в коде
        
        Args:
            code: Код для анализа
            focus: Область фокуса (logic, performance, security, etc.)
        
        Returns:
            Список найденных проблем
        """
        task = f"Найди потенциальные баги{' с фокусом на ' + focus if focus else ''} в следующем коде:"
        context = {"code": code, "focus": focus}
        return await self.execute(task, context)
    
    async def suggest_test_cases(
        self,
        function_description: str,
        signature: Optional[str] = None
    ) -> dict:
        """
        Предложение тест-кейсов
        
        Args:
            function_description: Описание функции
            signature: Сигнатура функции (если есть)
        
        Returns:
            Список тест-кейсов
        """
        task = f"Предложи тест-кейсы для функции: {function_description}"
        if signature:
            task += f"\n\nСигнатура: {signature}"
        context = {"function": function_description, "signature": signature}
        return await self.execute(task, context)
    
    async def analyze_test_coverage(
        self,
        code: str,
        existing_tests: Optional[str] = None
    ) -> dict:
        """
        Анализ покрытия тестами
        
        Args:
            code: Код для анализа
            existing_tests: Существующие тесты (если есть)
        
        Returns:
            Анализ покрытия и рекомендации
        """
        task = "Проанализируй покрытие тестами и предложи что еще нужно протестировать:"
        context = {"code": code}
        if existing_tests:
            context["existing_tests"] = existing_tests
        return await self.execute(task, context)

