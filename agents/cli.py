"""CLI интерфейс для работы с агентами"""
import asyncio
import sys
import argparse
import json
import os
from typing import Optional
from agents.orchestrator import get_orchestrator

# Устанавливаем UTF-8 для вывода в Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


async def main_async(args):
    """Асинхронная основная функция"""
    orchestrator = get_orchestrator()
    
    if args.command == "execute":
        # Выполнение задачи
        result = await orchestrator.execute_task(
            task=args.task,
            task_type=args.type if args.type != "auto" else None,
            context=json.loads(args.context) if args.context else None
        )
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТ:")
        print("="*60)
        if result.get("success"):
            print(f"\n✅ Задача выполнена успешно агентом: {result.get('agent_used')}")
            print(f"\nРезультат:\n{result.get('result', result.get('raw_output', ''))}")
        else:
            print(f"\n❌ Ошибка: {result.get('error')}")
        print("="*60)
        return result.get("success", False)
    
    elif args.command == "plan":
        # Планирование и выполнение
        result = await orchestrator.plan_and_execute(
            goal=args.goal,
            context=json.loads(args.context) if args.context else None
        )
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТ ПЛАНИРОВАНИЯ И ВЫПОЛНЕНИЯ:")
        print("="*60)
        if result.get("success"):
            print("\n✅ План создан и выполнен")
            print(f"\nПлан:\n{result.get('plan', '')}")
            exec_result = result.get("execution", {})
            if exec_result.get("success"):
                print(f"\nРезультат выполнения:\n{exec_result.get('result', '')}")
            else:
                print(f"\nОшибка выполнения: {exec_result.get('error')}")
        else:
            print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        print("="*60)
        return result.get("success", False)
    
    elif args.command == "pipeline":
        # Выполнение пайплайна
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
        else:
            tasks_data = json.loads(args.tasks)
        
        result = await orchestrator.execute_pipeline(
            tasks=tasks_data,
            context=json.loads(args.context) if args.context else None
        )
        print("\n" + "="*60)
        print(f"РЕЗУЛЬТАТ ПАЙПЛАЙНА ({len(result)} шагов):")
        print("="*60)
        for i, step_result in enumerate(result):
            print(f"\n--- Шаг {i+1} ---")
            if step_result.get("success"):
                print(f"✅ Успешно ({step_result.get('agent_used')})")
                print(f"Результат: {str(step_result.get('result', ''))[:200]}...")
            else:
                print(f"❌ Ошибка: {step_result.get('error')}")
        print("="*60)
        return all(r.get("success", False) for r in result)
    
    elif args.command == "review":
        # Код-ревью
        code = args.code
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                code = f.read()
        
        result = await orchestrator.review_code(
            code=code,
            focus=args.focus
        )
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТ КОД-РЕВЬЮ:")
        print("="*60)
        reviews = result.get("reviews", {})
        for agent_name, review in reviews.items():
            print(f"\n--- {agent_name.upper()} ---")
            if review.get("success"):
                print(f"✅ {review.get('result', '')[:300]}...")
            else:
                print(f"❌ Ошибка: {review.get('error')}")
        print("="*60)
        return result.get("success", False)
    
    elif args.command == "agents":
        # Информация об агентах
        agents_info = orchestrator.get_agents_info()
        print("\n" + "="*60)
        print("ДОСТУПНЫЕ АГЕНТЫ:")
        print("="*60)
        for agent_name, info in agents_info.items():
            status = "✅ Включен" if info.get("enabled") else "❌ Отключен"
            print(f"\n{agent_name.upper()}:")
            print(f"  Имя: {info.get('name')}")
            print(f"  Роль: {info.get('role')}")
            print(f"  Статус: {status}")
        print("="*60)
        return True
    
    else:
        print(f"Неизвестная команда: {args.command}")
        return False


def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description="CLI для работы с агентами OpenCode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Выполнение задачи через автоматический выбор агента
  python -m agents.cli execute -t "Реализуй функцию для парсинга дат"

  # Выполнение задачи через конкретного агента
  python -m agents.cli execute -t "Создай план разработки" --type planning

  # Планирование и выполнение
  python -m agents.cli plan -g "Добавить систему отзывов"

  # Код-ревью
  python -m agents.cli review --file handlers/user_handlers.py --focus security

  # Информация об агентах
  python -m agents.cli agents
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Команда")
    
    # Команда execute
    execute_parser = subparsers.add_parser("execute", help="Выполнить задачу")
    execute_parser.add_argument("-t", "--task", required=True, help="Описание задачи")
    execute_parser.add_argument("--type", default="auto", choices=["auto", "planning", "development", "documentation", "testing"],
                                help="Тип задачи (по умолчанию: auto)")
    execute_parser.add_argument("--context", help="Контекст в формате JSON")
    
    # Команда plan
    plan_parser = subparsers.add_parser("plan", help="Планирование и выполнение")
    plan_parser.add_argument("-g", "--goal", required=True, help="Цель/задача")
    plan_parser.add_argument("--context", help="Контекст в формате JSON")
    
    # Команда pipeline
    pipeline_parser = subparsers.add_parser("pipeline", help="Выполнить пайплайн задач")
    pipeline_group = pipeline_parser.add_mutually_exclusive_group(required=True)
    pipeline_group.add_argument("--tasks", help="Задачи в формате JSON")
    pipeline_group.add_argument("--file", help="Файл с задачами в формате JSON")
    pipeline_parser.add_argument("--context", help="Контекст в формате JSON")
    
    # Команда review
    review_parser = subparsers.add_parser("review", help="Код-ревью")
    review_group = review_parser.add_mutually_exclusive_group(required=True)
    review_group.add_argument("--code", help="Код для ревью")
    review_group.add_argument("--file", help="Файл с кодом для ревью")
    review_parser.add_argument("--focus", help="Область фокуса (security, performance, style)")
    
    # Команда agents
    subparsers.add_parser("agents", help="Показать информацию об агентах")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Запускаем асинхронную функцию
    success = asyncio.run(main_async(args))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

