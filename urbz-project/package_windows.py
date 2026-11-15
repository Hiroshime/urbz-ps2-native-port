#!/usr/bin/env python3
"""Assemble a private Windows prototype from this local build and disc."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    config = json.loads((ROOT / "urbz-project/game.json").read_text())
    iso = (ROOT / "games/urbz-pal/disc.iso").resolve()
    out = ROOT / "dist/Urbz-PS2-Windows"
    out.mkdir(parents=True, exist_ok=True)
    (out / "user").mkdir(exist_ok=True)
    template = out / "empty-card.ps2"
    if not template.exists():
        subprocess.run([sys.executable, str(ROOT / "scripts/mcformat.py"), str(template), "--date", "2026-01-01 00:00:00"], check=True)
    for source, name in [
        (ROOT / "build/wine-urbz-pal/ps2run.exe", "Urbz.exe"),
        (ROOT / "build/wine-urbz-pal/SDL2.dll", "SDL2.dll"),
        (ROOT / "tools/wine-bench/dxc/dxcompiler.dll", "dxcompiler.dll"),
        (ROOT / "tools/wine-bench/dxc/dxil.dll", "dxil.dll"),
        (ROOT / "games/urbz-pal/entries.txt", "entries.txt"),
        (ROOT / "LICENSE", "LICENSE-runtime.txt"),
        (ROOT / "urbz-project/LAN-Windows.ps1", "LAN-Windows.ps1"),
        (ROOT / "urbz-project/LAN.md", "LAN.md"),
        (ROOT / "urbz-project/INTERNET.md", "INTERNET.md"),
        (ROOT / "urbz-project/graphics-presets.json", "graphics-presets.json"),
        (ROOT / "urbz-project/Graphics-Windows.ps1", "Graphics-Windows.ps1"),
        (ROOT / "urbz-project/Configure-Graphics-Windows.ps1", "Configure-Graphics-Windows.ps1"),
        (ROOT / "urbz-project/Play-Windows.ps1", "Play-Windows.ps1"),
        (ROOT / "urbz-project/GRAFICOS.md", "GRAFICOS.md"),
        (ROOT / "urbz-project/GRAFICOS-RESULTADOS.md", "GRAFICOS-RESULTADOS.md"),
        (ROOT / "urbz-project/DESEMPENHO.md", "DESEMPENHO.md"),
        (ROOT / "urbz-project/FPS-INVESTIGACAO.md", "FPS-INVESTIGACAO.md"),
    ]:
        if name.endswith(".ps1"):
            # Windows PowerShell 5.1 needs a BOM to read the Portuguese messages.
            (out / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8-sig")
        elif name.endswith(".md"):
            (out / name).write_text(source.read_text().replace("../games/urbz-pal/validation/graphics/", "graphics-comparison/").replace("../games/urbz-pal/validation/performance/", "performance-comparison/"), encoding="utf-8")
        else:
            shutil.copy2(source, out / name)
    comparison = ROOT / "games/urbz-pal/validation/graphics"
    if (comparison / "comparacao.html").exists():
        for relative in ["comparacao.html", "comparacao.png", "desempenho.png", "report.json"] + [
            f"{scale}x/trial-1/shots/frame_18080.png" for scale in range(1, 5)
        ]:
            target = out / "graphics-comparison" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(comparison / relative, target)
    performance = ROOT / "games/urbz-pal/validation/performance"
    if (performance / "report.json").exists():
        for relative in ["report.json", "desempenho-comparado.png", "high-fps/report.json", "high-fps/threading-strict-report.json"]:
            source = performance / relative
            if source.exists():
                target = out / "performance-comparison" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    # Keep the compiler needed by previously unseen EE/VU programs. The complete
    # upstream toolchain is used here; trimming it is a later packaging task.
    shutil.copytree(ROOT / "tools/wine-bench/win-llvm-mingw", out / "compiler", dirs_exist_ok=True)
    shutil.copytree(ROOT / "urbz-project/licenses", out / "licenses", dirs_exist_ok=True)
    target_iso = out / "disc.iso"
    if not target_iso.exists():
        subprocess.run(["cp", "--reflink=auto", "--", str(iso), str(target_iso)], check=True)
    with target_iso.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != config["iso_sha256"]:
            raise SystemExit("A ISO no pacote não corresponde à revisão configurada; nada foi sobrescrito.")
    launcher = '''@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Play-Windows.ps1" %*
set "URBZ_RESULT=%ERRORLEVEL%"
if errorlevel 1 pause
exit /b %URBZ_RESULT%
'''
    (out / "Jogar-Windows.cmd").write_bytes(launcher.replace("\n", "\r\n").encode("utf-8"))
    configure = '''@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Configure-Graphics-Windows.ps1" %*
set "URBZ_RESULT=%ERRORLEVEL%"
if errorlevel 1 pause
exit /b %URBZ_RESULT%
'''
    (out / "Configurar-Graficos.cmd").write_bytes(configure.replace("\n", "\r\n").encode("utf-8"))
    for role, name, internet in [("Host", "Hospedar-LAN.cmd", ""), ("Join", "Entrar-LAN.cmd", ""),
                                ("Host", "Hospedar-Internet.cmd", "-Internet"), ("Join", "Entrar-Internet.cmd", "-Internet")]:
        text = f'''@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0LAN-Windows.ps1" -Role {role} {internet} %*
set "URBZ_RESULT=%ERRORLEVEL%"
if errorlevel 1 pause
exit /b %URBZ_RESULT%
'''
        (out / name).write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    (out / "LEIA-ME.txt").write_text(
        "The Urbz PS2 PAL - protótipo local\n\n"
        "Abra Jogar-Windows.cmd. F1 mostra os controles; F5 salva um estado e F8 carrega.\n"
        "Conecte dois controles para usar o modo local 2 Player.\n"
        "Saves e gravações ficam em user.\n\n"
        "Build Windows verificado via Wine/Vulkan. Ainda falta teste em Windows real.\n"
        "Este build requer CPU com AVX2.\n"
        "Gráficos opcionais: abra Configurar-Graficos.cmd e escolha padrao, original, hd, alto ou ultra. Leia GRAFICOS.md.\n"
        "Por execução: Jogar-Windows.cmd -Graphics hd. Os atalhos de rede também aceitam -Graphics.\n"
        "Em rede, use a mesma resolução interna e filtro 2D nos dois PCs; configurações incompatíveis são rejeitadas.\n"
        "LAN experimental: abra Hospedar-LAN.cmd em um PC e Entrar-LAN.cmd no outro.\n"
        "Leia LAN.md. Cada PC precisa da mesma revisão de build e da mesma ISO.\n"
        "Cada jogador usa o primeiro controle/teclado de seu PC; escolha 2 Player no jogo.\n"
        "O cartão compartilhado fica em user/lan-host/card.ps2; o anfitrião é a referência.\n"
        "O cliente recebe o cartão antes de começar. Salve pelo menu do jogo; F1/F5/F8 ficam desativados em rede.\n"
        "Internet direta: use Hospedar-Internet.cmd / Entrar-Internet.cmd, com IPv4 público e chave da partida.\n"
        "O anfitrião precisa encaminhar TCP 27888 no roteador e verificar se tem entrada por IPv4 público. Leia INTERNET.md.\n"
        "A conexão usa TLS antes de transferir o cartão. Não depende de VPN ou conta externa.\n"
        "Validado em loopback Linux/Windows via Wine; dois PCs físicos e Internet ainda não foram testados.\n"
        "O jogo completo não foi certificado.\n",
        encoding="utf-8")
    (out / "prototype.json").write_text(json.dumps(config, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
