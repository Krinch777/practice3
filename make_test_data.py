"""ПР1. Создаёт тестовые «данные компании» для резервного копирования.
Вариант 15: отделы design, print, buh — по 6 файлов на отдел.
"""
import random
from pathlib import Path

root = Path("company_data")
DEPARTMENTS = ["design", "print", "buh"]   # вариант 15
FILES_PER_DEPT = 6                         # вариант 15

for dept in DEPARTMENTS:
    (root / dept).mkdir(parents=True, exist_ok=True)
    for i in range(1, FILES_PER_DEPT + 1):
        lines = [f"{dept};doc{i};{random.randint(1000, 99999)}" for _ in range(200)]
        (root / dept / f"report_{i}.csv").write_text("\n".join(lines), encoding="utf-8")

print(f"Тестовые данные созданы в папке company_data/ "
      f"({len(DEPARTMENTS)} отдела × {FILES_PER_DEPT} файлов)")
