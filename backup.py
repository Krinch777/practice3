"""ПР1. Резервное копирование с ротацией и проверкой целостности.
Вариант 15 (Квитко Дмитрий Сергеевич): KEEP_LAST = 5.

Запуск:
    python backup.py                     — создать копию, ротация, проверка
    python backup.py verify [архив]      — проверить копию (по умолчанию последнюю)
    python backup.py restore [архив]     — восстановить данные (по умолчанию из последней)
"""
import hashlib
import json
import shutil
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

SOURCE = Path("company_data")   # что копируем
BACKUP_DIR = Path("backups")    # куда складываем архивы
KEEP_LAST = 5                   # сколько последних копий хранить (вариант 15)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_manifest(folder):
    """Контрольная сумма каждого файла: {относительный_путь: sha256}."""
    return {p.relative_to(folder).as_posix(): sha256(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}


def manifest_path(archive):
    """backups/backup_X.tar.gz -> backups/backup_X.json"""
    return archive.with_suffix("").with_suffix(".json")


def create_backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = BACKUP_DIR / f"backup_{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(SOURCE, arcname=SOURCE.name)
    manifest = {"created": stamp, "archive_sha256": sha256(archive),
                "files": make_manifest(SOURCE)}
    manifest_path(archive).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Создан {archive.name}, файлов: {len(manifest['files'])}, "
          f"размер: {archive.stat().st_size / 1024:.1f} КБ")
    return archive


def rotate():
    archives = sorted(BACKUP_DIR.glob("backup_*.tar.gz"))
    for old in archives[:-KEEP_LAST]:
        old.unlink()
        manifest_path(old).unlink(missing_ok=True)
        print(f"[ROTATE] Удалена старая копия {old.name}")


# ---------- Задание 3: подробный отчёт о различиях ----------
def compare_manifests(restored, expected):
    """Сравнивает словари {файл: хеш}. Возвращает (missing, extra, changed).

    missing — файлы есть в манифесте, но не восстановились из архива;
    extra   — файлы восстановились из архива, но в манифесте их нет (лишние);
    changed — файл есть в обоих местах, но хеши различаются.
    """
    missing = sorted(set(expected) - set(restored))
    extra = sorted(set(restored) - set(expected))
    changed = sorted(f for f in set(expected) & set(restored)
                     if expected[f] != restored[f])
    return missing, extra, changed


def verify_restore(archive):
    """Восстанавливает архив во временную папку и сравнивает контрольные суммы."""
    manifest = json.loads(manifest_path(archive).read_text(encoding="utf-8"))
    if sha256(archive) != manifest["archive_sha256"]:
        print("[FAIL] Архив повреждён: контрольная сумма не совпадает")
        return False
    tmp = Path("restore_test")
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        with tarfile.open(archive) as tar:
            tar.extractall(tmp, filter="data")
    except (tarfile.TarError, EOFError, OSError) as e:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[FAIL] Архив повреждён: не удалось распаковать ({e})")
        return False
    restored = make_manifest(tmp / SOURCE.name)
    shutil.rmtree(tmp)
    if restored == manifest["files"]:
        print(f"[OK] Восстановление проверено: {len(restored)} файлов совпадают")
        return True

    missing, extra, changed = compare_manifests(restored, manifest["files"])
    print("[FAIL] Восстановленные данные не совпадают с оригиналом")
    for f in missing:
        print(f"   [ОТСУТСТВУЕТ] {f}")
    for f in extra:
        print(f"   [ЛИШНИЙ]      {f}")
    for f in changed:
        print(f"   [ИЗМЕНЁН]     {f}")
    print(f"   Итого: отсутствует {len(missing)}, лишних {len(extra)}, "
          f"изменено {len(changed)}")
    return False


# ---------- Задание 4: восстановление после инцидента ----------
def restore(archive):
    """Восстанавливает company_data из выбранного архива в текущую папку."""
    start = time.perf_counter()
    manifest = json.loads(manifest_path(archive).read_text(encoding="utf-8"))
    if sha256(archive) != manifest["archive_sha256"]:
        print(f"[FAIL] Архив {archive.name} повреждён, восстановление отменено")
        return False

    print(f"[RESTORE] Восстановление из {archive.name} ...")
    shutil.rmtree(SOURCE, ignore_errors=True)        # удаляем повреждённую папку
    with tarfile.open(archive) as tar:
        tar.extractall(Path("."), filter="data")

    restored = make_manifest(SOURCE)
    ok = restored == manifest["files"]
    elapsed = time.perf_counter() - start
    status = "[OK] Данные восстановлены" if ok else "[WARN] Восстановлено с расхождениями"
    print(f"{status}: {len(restored)} файлов")
    print(f"[TIME] Время восстановления: {elapsed:.3f} с")
    return ok


def latest_backup():
    archives = sorted(BACKUP_DIR.glob("backup_*.tar.gz"))
    if not archives:
        sys.exit("[ERROR] В папке backups/ нет ни одной копии")
    return archives[-1]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "backup"
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if cmd == "verify":
        verify_restore(target or latest_backup())
    elif cmd == "restore":
        restore(target or latest_backup())
    else:
        archive = create_backup()
        rotate()
        verify_restore(archive)
