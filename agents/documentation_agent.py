"""Агент документации"""
from agents.base_agent import BaseAgent
from typing import Optional


class DocumentationAgent(BaseAgent):
    """Агент для создания и обновления документации"""
    
    def __init__(self):
        system_prompt = """Ты эксперт по техническому писательству и документации.
Твоя задача - создавать понятную, структурированную документацию для разработчиков и пользователей.

Требования к документации:
1. Понятный язык (русский)
2. Четкая структура
3. Примеры использования
4. Описание параметров и возвращаемых значений
5. Примеры кода (если применимо)
6. Использование markdown форматирования

Отвечай на русском языке. Документация должна быть полезной и полной."""
        
        super().__init__(
            name="DocumentationAgent",
            role="Документатор",
            system_prompt=system_prompt
        )
    
    def _get_task_instructions(self) -> str:
        return """Создай документацию, включив:
1. Описание функциональности
2. Параметры и их типы
3. Возвращаемые значения
4. Примеры использования
5. Примечания и предупреждения (если есть)

Используй markdown форматирование."""
    
    async def document_code(
        self,
        code: str,
        doc_type: str = "docstring"
    ) -> dict:
        """
        Документирование кода
        
        Args:
            code: Код для документирования
            doc_type: Тип документации (docstring, readme, api_docs)
        
        Returns:
            Документация
        """
        task = f"Создай {doc_type} документацию для следующего кода:"
        context = {"code": code, "doc_type": doc_type}
        return await self.execute(task, context)
    
    async def create_readme(
        self,
        project_info: dict,
        sections: Optional[list[str]] = None
    ) -> dict:
        """
        Создание README файла
        
        Args:
            project_info: Информация о проекте
            sections: Разделы для включения
        
        Returns:
            README содержимое
        """
        sections_str = ", ".join(sections) if sections else "стандартные разделы"
        task = f"Создай README.md со следующими разделами: {sections_str}"
        context = {"project_info": project_info, "sections": sections}
        return await self.execute(task, context)
    
    async def update_changelog(
        self,
        changes: list[str],
        version: Optional[str] = None
    ) -> dict:
        """
        Обновление CHANGELOG
        
        Args:
            changes: Список изменений
            version: Версия (если не указана, добавится автоматически)
        
        Returns:
            Запись для CHANGELOG
        """
        changes_str = "\n".join(f"- {c}" for c in changes)
        task = f"Создай запись в CHANGELOG для версии {version or 'следующей'}:\n\n{changes_str}"
        context = {"changes": changes, "version": version}
        return await self.execute(task, context)
    
    async def write_api_docs(
        self,
        functions: list[dict],
        format: str = "markdown"
    ) -> dict:
        """
        Написание API документации
        
        Args:
            functions: Список функций с описаниями
            format: Формат документации
        
        Returns:
            API документация
        """
        task = f"Создай API документацию в формате {format} для следующих функций:"
        context = {"functions": functions, "format": format}
        return await self.execute(task, context)

