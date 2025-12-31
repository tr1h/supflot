#!/usr/bin/env python3
"""Быстрый скрипт для работы с агентами из Cursor"""
import asyncio
import sys
from agents.orchestrator import get_orchestrator


async def quick_task(task: str, agent_type: str = "auto"):
    """Быстрое выполнение задачи через агента"""
    orchestrator = get_orchestrator()
    
    print(f"\n🤖 Выполняю задачу через агента '{agent_type}'...\n")
    
    result = await orchestrator.execute_task(task, agent_type)
    
    if result.get("success"):
        print("✅ Успешно!\n")
        print("="*60)
        print(result.get("result", result.get("raw_output", "")))
        print("="*60)
        return True
    else:
        print(f"❌ Ошибка: {result.get('error')}")
        return False


async def quick_plan(goal: str):
    """Быстрое планирование"""
    orchestrator = get_orchestrator()
    
    print(f"\n📋 Планирую: {goal}\n")
    
    result = await orchestrator.plan_and_execute(goal)
    
    if result.get("success"):
        print("✅ План создан!\n")
        print("="*60)
        print("ПЛАН:")
        print("="*60)
        print(result.get("plan", ""))
        print("="*60)
        return True
    else:
        print(f"❌ Ошибка: {result.get('error')}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python quick_agent.py 'ваша задача' [agent_type]")
        print("  python quick_agent.py plan 'ваша цель'")
        print("\nПримеры:")
        print("  python quick_agent.py 'Реализуй функцию parse_date'")
        print("  python quick_agent.py 'Создай план' planning")
        print("  python quick_agent.py plan 'Добавить систему отзывов'")
        sys.exit(1)
    
    if sys.argv[1] == "plan":
        goal = " ".join(sys.argv[2:])
        success = asyncio.run(quick_plan(goal))
    else:
        task = " ".join(sys.argv[1:-1]) if len(sys.argv) > 2 else sys.argv[1]
        agent_type = sys.argv[-1] if len(sys.argv) > 2 and sys.argv[-1] in ["planning", "development", "documentation", "testing"] else "auto"
        success = asyncio.run(quick_task(task, agent_type))
    
    sys.exit(0 if success else 1)

