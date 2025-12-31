"""Сервис для работы с AI через OpenCode"""
import asyncio
import logging
import subprocess
import platform
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для работы с AI через OpenCode"""
    
    def __init__(self):
        self.opencode_path = self._get_opencode_path()
        self.enabled = self._check_opencode_available()
    
    def _get_opencode_path(self) -> str:
        """Определение пути к OpenCode"""
        # В WSL используется путь ~/.opencode/bin/opencode
        # В Linux/macOS тоже
        if platform.system() == "Windows":
            # В Windows через WSL
            return "wsl"
        return "opencode"
    
    def _check_opencode_available(self) -> bool:
        """Проверка доступности OpenCode"""
        try:
            if platform.system() == "Windows":
                # Проверяем через WSL
                result = subprocess.run(
                    ["wsl", "bash", "-c", "which opencode || test -f ~/.opencode/bin/opencode"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            else:
                result = subprocess.run(
                    ["which", "opencode"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception as e:
            logger.warning(f"OpenCode availability check failed: {e}")
            return False
    
    async def _call_opencode(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Вызов OpenCode с промптом"""
        if not self.enabled and not Config.AI_ENABLED:
            logger.debug("OpenCode is not available or disabled")
            return None
        
        try:
            # Формируем полный промпт
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            # Используем asyncio.to_thread для выполнения синхронного subprocess
            def run_opencode():
                import tempfile
                import os
                
                # Создаем временный файл с промптом
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                    f.write(full_prompt)
                    temp_file = f.name
                
                try:
                    if platform.system() == "Windows":
                        # В Windows используем WSL
                        cmd = [
                            "wsl", "bash", "-c",
                            f"export PATH=$HOME/.opencode/bin:$PATH && cat {temp_file} | ~/.opencode/bin/opencode 2>/dev/null || cat {temp_file} | opencode"
                        ]
                    else:
                        cmd = [
                            "bash", "-c",
                            f"cat {temp_file} | ~/.opencode/bin/opencode 2>/dev/null || cat {temp_file} | opencode"
                        ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        encoding='utf-8',
                        errors='ignore'
                    )
                    
                    if result.returncode != 0:
                        logger.error(f"OpenCode error (code {result.returncode}): {result.stderr[:200]}")
                        return None
                    
                    output = result.stdout.strip()
                    return output if output else None
                    
                finally:
                    # Удаляем временный файл
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            
            result = await asyncio.to_thread(run_opencode)
            return result
            
        except subprocess.TimeoutExpired:
            logger.error("OpenCode request timed out")
            return None
        except Exception as e:
            logger.error(f"Error calling OpenCode: {e}", exc_info=True)
            return None
    
    async def generate_board_description(
        self,
        board_name: str,
        price: float,
        additional_info: Optional[str] = None
    ) -> Optional[str]:
        """Генерация описания для доски"""
        system_prompt = """Ты помощник для сервиса аренды SUP-досок. 
Твоя задача - создать краткое, привлекательное описание SUP-доски для клиентов.
Описание должно быть на русском языке, 1-2 предложения, информативное и заманчивое."""
        
        prompt = f"Создай описание для SUP-доски '{board_name}' с ценой {price}₽/час"
        if additional_info:
            prompt += f". Дополнительная информация: {additional_info}"
        prompt += "."
        
        result = await self._call_opencode(prompt, system_prompt)
        if result:
            # Очищаем результат от лишних символов
            result = result.strip().strip('"').strip("'")
            # Ограничиваем длину
            if len(result) > 300:
                result = result[:297] + "..."
        return result
    
    async def answer_user_question(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Ответ на вопрос пользователя"""
        system_prompt = """Ты помощник для сервиса аренды SUP-досок SUPFLOT.
Твоя задача - отвечать на вопросы пользователей вежливо, кратко и информативно.
Используй только информацию о сервисе аренды SUP-досок. Если вопрос не связан с сервисом, вежливо перенаправь к команде /contacts."""
        
        prompt = f"Вопрос пользователя: {question}"
        if context:
            prompt += f"\n\nКонтекст: {context}"
        prompt += "\n\nДай краткий ответ (1-3 предложения):"
        
        result = await self._call_opencode(prompt, system_prompt)
        if result:
            result = result.strip().strip('"').strip("'")
            if len(result) > 500:
                result = result[:497] + "..."
        return result
    
    async def parse_date_from_text(self, text: str) -> Optional[str]:
        """Парсинг даты из естественного языка"""
        system_prompt = """Ты помощник для парсинга дат. 
Твоя задача - извлечь дату из текста на русском языке и вернуть её в формате ДД.ММ.ГГГГ.
Если дату нельзя определить, верни только слово "НЕТ"."""
        
        prompt = f"Извлеки дату из текста: '{text}'\n\nВерни только дату в формате ДД.ММ.ГГГГ или 'НЕТ' если дату нельзя определить."
        
        result = await self._call_opencode(prompt, system_prompt)
        if result:
            result = result.strip().strip('"').strip("'").upper()
            if result == "НЕТ" or len(result) < 8:
                return None
            return result
        return None
    
    async def generate_support_response(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Генерация ответа службы поддержки"""
        system_prompt = """Ты представитель службы поддержки сервиса аренды SUP-досок SUPFLOT.
Отвечай вежливо, профессионально и полезно. Предлагай конкретные действия.
Используй эмодзи для дружелюбного тона."""
        
        context_str = ""
        if user_context:
            bookings_count = user_context.get("bookings_count", 0)
            if bookings_count > 0:
                context_str = f"У пользователя есть {bookings_count} активных бронирований."
        
        prompt = f"Сообщение пользователя: {user_message}"
        if context_str:
            prompt += f"\n\n{context_str}"
        prompt += "\n\nДай профессиональный и полезный ответ:"
        
        result = await self._call_opencode(prompt, system_prompt)
        if result:
            result = result.strip().strip('"').strip("'")
            if len(result) > 1000:
                result = result[:997] + "..."
        return result


# Глобальный экземпляр сервиса
_ai_service_instance: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Получение глобального экземпляра AI сервиса"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance

