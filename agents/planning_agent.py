"""Агент планирования"""
from agents.base_agent import BaseAgent


class PlanningAgent(BaseAgent):
    """Агент для планирования задач и разработки"""
    
    def __init__(self):
        system_prompt = """Ты эксперт по планированию разработки ПО.
Твоя задача - создавать четкие, структурированные планы для реализации функций и исправления багов.

Требования к плану:
1. Четкая структура с шагами
2. Приоритизация задач
3. Учет зависимостей между задачами
4. Оценка сложности (если возможно)
5. Указание необходимых ресурсов

Отвечай на русском языке. Планы должны быть конкретными и выполнимыми."""
        
        super().__init__(
            name="PlanningAgent",
            role="Планировщик",
            system_prompt=system_prompt
        )
    
    def _get_task_instructions(self) -> str:
        return """Создай детальный план выполнения задачи.
Включи:
- Разбивку на этапы
- Приоритеты задач
- Зависимости между задачами
- Что нужно сделать на каждом этапе
- Рекомендации по реализации"""
    
    async def create_roadmap(
        self,
        features: list[str],
        context: dict = None
    ) -> dict:
        """
        Создание roadmap для списка функций
        
        Args:
            features: Список функций для планирования
            context: Контекст проекта
        
        Returns:
            Roadmap с планом реализации
        """
        task = f"Создай roadmap для следующих функций:\n" + "\n".join(f"- {f}" for f in features)
        return await self.execute(task, context)
    
    async def prioritize_tasks(
        self,
        tasks: list[str],
        criteria: str = "value and effort"
    ) -> dict:
        """
        Приоритизация задач
        
        Args:
            tasks: Список задач
            criteria: Критерии приоритизации
        
        Returns:
            Приоритизированный список задач
        """
        task = f"Приоритизируй следующие задачи по критерию '{criteria}':\n" + "\n".join(f"- {t}" for t in tasks)
        context = {"criteria": criteria}
        return await self.execute(task, context)

