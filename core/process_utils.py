import os

import psutil


def kill_other_instances(app_root: str, main_name: str = "main.py") -> None:
    """
    Encerra outros processos Python do mesmo app.
    Identifica por cmdline contendo o app_root e/ou main_name.
    """
    app_root = os.path.abspath(app_root)
    current_pid = os.getpid()

    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline", "cwd"]):
        try:
            pid = proc.info.get("pid")
            if pid == current_pid:
                continue

            cmdline = proc.info.get("cmdline") or []
            cwd = proc.info.get("cwd") or ""

            if not cmdline:
                continue

            # Heuristica: mesmo app se cmdline/cwd contém o root
            cmdline_joined = " ".join(cmdline)
            same_root = app_root in cmdline_joined or app_root in (cwd or "")
            has_main = any(os.path.basename(arg) == main_name for arg in cmdline)

            if same_root or has_main:
                try:
                    proc.terminate()
                except Exception:
                    pass
        except Exception:
            continue

    # Aguarda curto e força kill se necessário
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline", "cwd"]):
        try:
            pid = proc.info.get("pid")
            if pid == current_pid:
                continue
            cmdline = proc.info.get("cmdline") or []
            cwd = proc.info.get("cwd") or ""
            if not cmdline:
                continue
            cmdline_joined = " ".join(cmdline)
            same_root = app_root in cmdline_joined or app_root in (cwd or "")
            has_main = any(os.path.basename(arg) == main_name for arg in cmdline)
            if same_root or has_main:
                try:
                    proc.kill()
                except Exception:
                    pass
        except Exception:
            continue
