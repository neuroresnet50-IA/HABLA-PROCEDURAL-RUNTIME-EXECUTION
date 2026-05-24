#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from rich.align import Align
    from rich.box import HEAVY, ROUNDED
    from rich.console import Console, Group
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print("Missing dependency: rich")
    print("Run: python -m pip install -r installer/requirements.txt")
    sys.exit(1)

try:
    from requirement_planner import plan_from_requirement
except ImportError:
    plan_from_requirement = None


APP_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_ROOT = Path(__file__).resolve().parent
LOG_ROOT = INSTALLER_ROOT / "logs"
DEFAULT_TIMEOUT_SECONDS = 1800

console = Console()

LOGO = "HABLA\nOBSERVER IA\nINSTALLER"

PROFILE_DESCRIPTIONS = {
    "base": "App base: Git, Python venv, backend Flask, frontend Vite/React.",
    "base-stack": "Alias de base.",
    "db": "PostgreSQL y SQL Server por instalacion nativa o Docker.",
    "web-dev": "Node.js, npm, Vite, React, Angular CLI opcional y VS Code.",
    "ml-cpu": "Machine learning CPU: torch CPU, OpenCV, pandas, sklearn, notebooks.",
    "ml-nvidia": "Machine learning NVIDIA RTX: PyTorch CUDA, vision y pruebas CUDA.",
    "gen-ai": "IA generativa: transformers, datasets, accelerate y tooling LLM.",
    "vision-industrial": "Vision industrial: OpenCV contrib, YOLO/Ultralytics y albumentations.",
    "agents": "Stack de agentes IA, orquestacion, clientes API y herramientas.",
    "mlops": "Docker, Compose, MLflow, Jupyter y servicios auxiliares.",
    "hardware-io-utils": "Serial, pygame, automatizacion, scraping, documentos, testing, GUI y utilidades de sistema.",
    "data-viz-ml-nlp-extended": "Matplotlib ampliado, visualizacion, estadistica, finanzas, AutoML, NLP y busqueda vectorial.",
    "full": "Instalacion completa por perfiles.",
    "all": "Alias de full.",
}

PROFILE_GROUPS = {
    "base": ["base"],
    "base-stack": ["base"],
    "db": ["base", "db"],
    "web-dev": ["base", "web-dev"],
    "ml-cpu": ["base", "ml-cpu"],
    "ml-nvidia": ["base", "ml-nvidia"],
    "gen-ai": ["base", "gen-ai"],
    "vision-industrial": ["base", "vision-industrial"],
    "agents": ["base", "agents"],
    "mlops": ["base", "db", "mlops"],
    "hardware-io-utils": ["base", "hardware-io-utils"],
    "data-viz-ml-nlp-extended": ["base", "data-viz-ml-nlp-extended"],
    "full": ["base", "db", "web-dev", "ml-cpu", "ml-nvidia", "gen-ai", "vision-industrial", "agents", "mlops", "hardware-io-utils", "data-viz-ml-nlp-extended"],
    "all": ["base", "db", "web-dev", "ml-cpu", "ml-nvidia", "gen-ai", "vision-industrial", "agents", "mlops", "hardware-io-utils", "data-viz-ml-nlp-extended"],
}


@dataclass
class CommandSpec:
    label: str
    command: list[str]
    cwd: Path = APP_ROOT
    kind: str = "project"
    required: bool = True
    timeout: int = DEFAULT_TIMEOUT_SECONDS


@dataclass
class StepSpec:
    title: str
    commands: list[CommandSpec] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    progress: int = 0
    done: bool = False
    failed: bool = False
    skipped: bool = False


@dataclass
class InstallerState:
    profile: str
    execute: bool
    allow_system: bool
    groups: list[str] | None = None
    requirement_plan: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mode: str = "Detecting"
    total_progress: int = 0
    current_step: int = 0
    logs: list[str] = field(default_factory=list)
    system: dict[str, str] = field(default_factory=dict)
    components: list[tuple[str, str]] = field(default_factory=list)
    detected_gpu: str = "Not detected"
    cuda: str = "Not detected"
    degraded: bool = False
    report: dict[str, Any] = field(default_factory=dict)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def resolve_groups(state: InstallerState) -> list[str]:
    return state.groups or PROFILE_GROUPS.get(state.profile, ["base"])


def profile_description(state: InstallerState) -> str:
    if state.requirement_plan.get("description"):
        return str(state.requirement_plan["description"])
    return PROFILE_DESCRIPTIONS.get(state.profile, "Perfil calculado por requerimiento de cliente.")


def short_shell(command: list[str], timeout: int = 4) -> str:
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return output.strip()
    except Exception:
        return ""


def detect_package_manager() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "winget" if command_exists("winget") else "manual"
    if system == "darwin":
        return "brew" if command_exists("brew") else "manual"
    for candidate in ("apt-get", "dnf", "zypper", "pacman"):
        if command_exists(candidate):
            return candidate
    return "manual"


def detect_gpu() -> tuple[str, str, bool]:
    if command_exists("nvidia-smi"):
        name = short_shell(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
        driver = short_shell(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
        cuda = short_shell(["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"])
        gpu_name = name.splitlines()[0] if name else "NVIDIA detected"
        driver_value = driver.splitlines()[0] if driver else "driver unknown"
        cuda_value = cuda.splitlines()[0] if cuda else "CUDA unknown"
        return f"{gpu_name} | driver {driver_value}", cuda_value, False
    if platform.system().lower() == "darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        return "Apple Silicon / MPS possible", "MPS", False
    return "Not detected", "Not detected", True


def detect_system(state: InstallerState) -> None:
    gpu, cuda, degraded = detect_gpu()
    groups = resolve_groups(state)
    state.detected_gpu = gpu
    state.cuda = cuda
    state.degraded = degraded if "ml-nvidia" in groups else False
    package_manager = detect_package_manager()
    state.mode = "GPU/CUDA" if "ml-nvidia" in groups and not degraded else "CPU/base"
    if "ml-nvidia" in groups and degraded:
        state.mode = "degraded CPU fallback"

    state.system = {
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "python": sys.version.split()[0],
        "package_manager": package_manager,
        "git": "yes" if command_exists("git") else "missing",
        "node": short_shell(["node", "--version"]) if command_exists("node") else "missing",
        "npm": short_shell(["npm", "--version"]) if command_exists("npm") else "missing",
        "docker": short_shell(["docker", "--version"]) if command_exists("docker") else "missing",
        "psql": "yes" if command_exists("psql") else "missing",
        "sqlcmd": "yes" if command_exists("sqlcmd") else "missing",
        "gpu": gpu,
        "cuda": cuda,
    }


def add_log(state: InstallerState, message: str, ok: bool = True) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    status = "OK" if ok else "WARN"
    style = "green" if ok else "yellow"
    state.logs.append(f"[dim][{timestamp}][/dim] {message} [{style}]{status}[/{style}]")
    state.logs = state.logs[-12:]


def os_install_commands(state: InstallerState, groups: list[str]) -> list[CommandSpec]:
    manager = state.system.get("package_manager") or detect_package_manager()
    system = platform.system().lower()
    commands: list[CommandSpec] = []

    if system == "linux" and manager == "apt-get":
        packages = ["ca-certificates", "build-essential", "python3-venv"]
        if not command_exists("git"):
            packages.append("git")
        if not command_exists("curl"):
            packages.append("curl")
        if not command_exists("python3"):
            packages.append("python3")
        if not command_exists("pip3"):
            packages.append("python3-pip")
        if not command_exists("node"):
            packages.append("nodejs")
        if not command_exists("npm"):
            packages.append("npm")
        if "db" in groups:
            if not command_exists("psql"):
                packages.extend(["postgresql", "postgresql-client"])
        if "mlops" in groups and not command_exists("docker"):
            packages.append("docker.io")
        if "mlops" in groups and not short_shell(["docker", "compose", "version"]):
            packages.append("docker-compose-plugin")
        commands.append(CommandSpec("apt update", ["sudo", "apt-get", "update"], kind="system"))
        if packages:
            commands.append(CommandSpec("apt install base packages", ["sudo", "apt-get", "install", "-y", *packages], kind="system"))
        else:
            commands.append(
                CommandSpec(
                    "apt packages already installed",
                    [python_command(), "-c", "print('apt packages already installed')"],
                    required=False,
                )
            )
    elif system == "linux" and manager == "dnf":
        packages = ["git", "curl", "python3", "python3-pip", "nodejs", "npm", "gcc", "gcc-c++", "make"]
        if "db" in groups:
            packages.extend(["postgresql", "postgresql-server"])
        if "mlops" in groups:
            packages.extend(["docker", "docker-compose-plugin"])
        commands.append(CommandSpec("dnf install base packages", ["sudo", "dnf", "install", "-y", *packages], kind="system"))
    elif system == "darwin" and manager == "brew":
        packages = ["git", "python@3.12", "node"]
        if "db" in groups:
            packages.append("postgresql@16")
        if "web-dev" in groups:
            packages.append("visual-studio-code")
        commands.append(CommandSpec("brew install base packages", ["brew", "install", *packages], kind="system"))
        if "mlops" in groups:
            commands.append(CommandSpec("brew install Docker Desktop", ["brew", "install", "--cask", "docker"], kind="system", required=False))
    elif system == "windows" and manager == "winget":
        packages = [
            ("Git", "Git.Git"),
            ("Python", "Python.Python.3.12"),
            ("Node.js LTS", "OpenJS.NodeJS.LTS"),
        ]
        if "web-dev" in groups:
            packages.append(("Visual Studio Code", "Microsoft.VisualStudioCode"))
        if "mlops" in groups:
            packages.append(("Docker Desktop", "Docker.DockerDesktop"))
        if "db" in groups:
            packages.append(("PostgreSQL", "PostgreSQL.PostgreSQL"))
        for label, package_id in packages:
            commands.append(CommandSpec(f"winget install {label}", ["winget", "install", "--id", package_id, "-e"], kind="system", required=False))
    else:
        commands.append(
            CommandSpec(
                "manual system package manager required",
                ["python", "-c", "print('Install Git, Python, Node, Docker and DB packages manually for this OS')"],
                kind="manual",
                required=False,
            )
        )
    return commands


def venv_python() -> Path:
    if platform.system().lower() == "windows":
        return APP_ROOT / ".venv" / "Scripts" / "python.exe"
    return APP_ROOT / ".venv" / "bin" / "python"


def python_command() -> str:
    return sys.executable or "python3"


def build_steps(state: InstallerState) -> list[StepSpec]:
    groups = resolve_groups(state)
    py = str(venv_python())
    steps: list[StepSpec] = []

    steps.append(
        StepSpec(
            "Preflight: detect OS, GPU and tools",
            notes=[
                f"OS: {state.system.get('os')}",
                f"GPU: {state.detected_gpu}",
                f"Package manager: {state.system.get('package_manager')}",
            ],
        )
    )

    steps.append(StepSpec("Install system packages", commands=os_install_commands(state, groups)))

    steps.append(
        StepSpec(
            "Create Python virtual environment",
            commands=[
                CommandSpec("create .venv", [python_command(), "-m", "venv", ".venv"]),
                CommandSpec("upgrade pip", [py, "-m", "pip", "install", "--upgrade", "pip"]),
                CommandSpec("install backend requirements", [py, "-m", "pip", "install", "-r", "backend/requirements.txt"]),
            ],
        )
    )

    if "ml-cpu" in groups:
        steps.append(
            StepSpec(
                "Install ML CPU requirements",
                commands=[CommandSpec("install ML CPU stack", [py, "-m", "pip", "install", "-r", "installer/requirements/requirements-ml-cpu.txt"], timeout=3600)],
            )
        )

    if "ml-nvidia" in groups:
        if state.degraded:
            steps.append(
                StepSpec(
                    "NVIDIA ML profile degraded",
                    notes=["nvidia-smi was not detected. Installer will not install CUDA wheels automatically on this host."],
                )
            )
        else:
            steps.append(
                StepSpec(
                    "Install NVIDIA RTX ML requirements",
                    commands=[CommandSpec("install NVIDIA PyTorch stack", [py, "-m", "pip", "install", "-r", "installer/requirements/requirements-ml-nvidia.txt"], timeout=3600)],
                )
            )

    optional_requirement_files = {
        "gen-ai": "requirements-gen-ai.txt",
        "vision-industrial": "requirements-vision.txt",
        "agents": "requirements-agents.txt",
        "mlops": "requirements-mlops.txt",
        "hardware-io-utils": "requirements-hardware-io-utils.txt",
        "data-viz-ml-nlp-extended": "requirements-data-viz-ml-nlp-extended.txt",
    }
    for group, requirement_file in optional_requirement_files.items():
        if group in groups:
            required = group not in {"hardware-io-utils", "data-viz-ml-nlp-extended"}
            steps.append(
                StepSpec(
                    f"Install {group} Python requirements",
                    commands=[
                        CommandSpec(
                            f"install {group}",
                            [py, "-m", "pip", "install", "-r", f"installer/requirements/{requirement_file}"],
                            required=required,
                            timeout=3600,
                        )
                    ],
                )
            )

    steps.append(
        StepSpec(
            "Install and build frontend",
            commands=[
                CommandSpec("npm install frontend", ["npm", "install"], cwd=APP_ROOT / "frontend", timeout=1800),
                CommandSpec("npm build frontend", ["npm", "run", "build"], cwd=APP_ROOT / "frontend", timeout=1800),
            ],
        )
    )

    if "web-dev" in groups:
        steps.append(
            StepSpec(
                "Install web developer extras",
                commands=[CommandSpec("install Angular CLI", ["npm", "install", "-g", "@angular/cli"], kind="system", required=False, timeout=1800)],
            )
        )

    if "db" in groups or "mlops" in groups:
        steps.append(
            StepSpec(
                "Prepare Docker services",
                commands=[
                    CommandSpec("validate docker", ["docker", "--version"], required=False),
                    CommandSpec("validate compose", ["docker", "compose", "version"], required=False),
                ],
                notes=[
                    "Use installer/docker/docker-compose.db.yml for PostgreSQL and SQL Server.",
                    "Use installer/docker/docker-compose.mlops.yml for MLflow/Jupyter/Redis.",
                ],
            )
        )

    steps.append(
        StepSpec(
            "Run smoke checks",
            commands=[
                CommandSpec("compile backend", [py, "-m", "py_compile", "backend/app.py", "backend/auth_routes.py"]),
                CommandSpec("import Flask", [py, "-c", "import flask, flask_socketio, psycopg; print('backend imports ok')"]),
                CommandSpec("frontend bundle exists", [python_command(), "-c", "from pathlib import Path; assert Path('frontend/dist/index.html').is_file(); print('frontend build ok')"]),
            ],
        )
    )

    if "ml-nvidia" in groups and not state.degraded:
        steps.append(
            StepSpec(
                "Run CUDA inference smoke check",
                commands=[
                    CommandSpec(
                        "torch CUDA smoke",
                        [py, "-c", "import torch; print(torch.cuda.is_available()); assert torch.cuda.is_available(); x=torch.ones((2,2), device='cuda'); print(x.sum().item())"],
                    )
                ],
            )
        )

    steps.append(StepSpec("Write installation report"))
    return steps


def build_components(state: InstallerState) -> list[tuple[str, str]]:
    groups = resolve_groups(state)
    components = [
        ("Git", state.system.get("git", "unknown")),
        ("Python", state.system.get("python", "unknown")),
        ("Node", state.system.get("node", "unknown")),
        ("npm", state.system.get("npm", "unknown")),
        ("Flask backend", "planned"),
        ("Vite/React frontend", "planned"),
    ]
    if "db" in groups:
        components.extend([("PostgreSQL", state.system.get("psql", "planned")), ("SQL Server", state.system.get("sqlcmd", "docker/native planned"))])
    if "mlops" in groups:
        components.extend([("Docker", state.system.get("docker", "planned")), ("Docker Compose", "planned")])
    if "ml-cpu" in groups:
        components.extend([("PyTorch CPU", "planned"), ("OpenCV", "planned"), ("Jupyter", "planned")])
    if "ml-nvidia" in groups:
        components.extend([("NVIDIA GPU", state.detected_gpu), ("PyTorch CUDA", "degraded" if state.degraded else "planned")])
    if "gen-ai" in groups:
        components.extend([("Transformers", "planned"), ("Accelerate", "planned")])
    if "vision-industrial" in groups:
        components.extend([("Ultralytics", "planned"), ("Albumentations", "planned")])
    if "agents" in groups:
        components.extend([("Agent tooling", "planned"), ("Tool registry", "planned")])
    if "hardware-io-utils" in groups:
        components.extend([("Hardware/IO utils", "best-effort planned"), ("Automation/game/dev utils", "best-effort planned")])
    if "data-viz-ml-nlp-extended" in groups:
        components.extend([("Data viz/stat/AutoML/NLP extended", "best-effort planned"), ("Matplotlib ecosystem", "best-effort planned")])
    return components


def should_run_command(state: InstallerState, command: CommandSpec) -> tuple[bool, str]:
    if not state.execute:
        return False, "dry-run"
    if command.kind == "system" and not state.allow_system:
        return False, "system command requires --allow-system"
    if command.kind == "manual":
        return False, "manual action"
    executable = command.command[0]
    if executable in {"sudo", "winget", "brew", "docker", "npm"} and not command_exists(executable):
        return False, f"{executable} not found"
    return True, "execute"


def run_command(command: CommandSpec) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command.command,
            cwd=str(command.cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=command.timeout,
            check=False,
        )
        output = (result.stdout or "").strip()
        return result.returncode == 0, output[-4000:]
    except Exception as error:
        return False, str(error)


def run_step(state: InstallerState, step: StepSpec) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    if not step.commands:
        for note in step.notes:
            add_log(state, note)
        step.done = True
        step.progress = 100
        return {"title": step.title, "status": "noted", "records": records, "notes": step.notes}

    for idx, command in enumerate(step.commands, start=1):
        step.progress = int(((idx - 1) / max(1, len(step.commands))) * 100)
        runnable, reason = should_run_command(state, command)
        record = {
            "label": command.label,
            "command": command.command,
            "cwd": str(command.cwd),
            "kind": command.kind,
            "required": command.required,
            "ran": runnable,
            "reason": reason,
            "ok": True,
            "output": "",
        }
        if not runnable:
            record["ok"] = not command.required or reason in {"dry-run", "system command requires --allow-system", "manual action"}
            add_log(state, f"{command.label}: {reason}", ok=record["ok"])
        else:
            add_log(state, f"Running: {command.label}")
            ok, output = run_command(command)
            record["ok"] = ok
            record["output"] = output
            add_log(state, f"{command.label}: {'completed' if ok else 'failed'}", ok=ok)
        records.append(record)
        if not record["ok"] and command.required:
            step.failed = True
            break
    step.done = not step.failed
    step.progress = 100
    return {"title": step.title, "status": "failed" if step.failed else "completed", "records": records, "notes": step.notes}


def write_report(state: InstallerState, steps_report: list[dict[str, Any]]) -> Path:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = LOG_ROOT / f"install-report-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    payload = {
        "generatedAt": now_iso(),
        "profile": state.profile,
        "groups": resolve_groups(state),
        "requirementPlan": state.requirement_plan,
        "execute": state.execute,
        "allowSystem": state.allow_system,
        "mode": state.mode,
        "degraded": state.degraded,
        "system": state.system,
        "components": state.components,
        "steps": steps_report,
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    state.report = payload
    return report_path


def build_summary_lines(state: InstallerState, report_path: Path) -> list[str]:
    system = state.report.get("system", {}) if isinstance(state.report, dict) else state.system
    groups = state.report.get("groups") if isinstance(state.report, dict) else resolve_groups(state)
    lines = [
        "HABLA Observer IA - installation summary",
        f"Report: {report_path}",
        f"Profile: {state.profile}",
        f"Groups: {', '.join(groups or resolve_groups(state))}",
        f"Mode: {'EXECUTE' if state.execute else 'DRY-RUN'}",
        f"OS: {system.get('os', 'unknown')}",
        f"Python: {system.get('python', 'unknown')}",
        f"Node: {system.get('node', 'unknown')}",
        f"npm: {system.get('npm', 'unknown')}",
        f"Docker: {system.get('docker', 'unknown')}",
        "",
        "Installed / verified:",
    ]

    if state.execute:
        lines.extend(
            [
                "- System packages checked for the selected groups.",
                "- Project .venv created/updated.",
                "- Backend requirements installed/verified: Flask, Flask-CORS, Flask-SocketIO, eventlet, psycopg.",
            ]
        )
        if "db" in groups:
            lines.append("- Database stack selected: PostgreSQL native/client checks and SQL Server Docker/native plan.")
        if "ml-cpu" in groups:
            lines.append("- ML CPU stack installed/verified: torch CPU, torchvision, torchaudio, OpenCV, numpy, pandas, matplotlib, seaborn, scikit-learn, JupyterLab, TensorBoard.")
        if "ml-nvidia" in groups:
            lines.append("- NVIDIA RTX stack selected: PyTorch CUDA wheels when nvidia-smi/CUDA are available.")
        if "gen-ai" in groups:
            lines.append("- Generative AI stack installed/verified: transformers, datasets, accelerate, safetensors, sentencepiece, tokenizers, peft, diffusers.")
        if "vision-industrial" in groups:
            lines.append("- Industrial vision stack installed/verified: OpenCV/cv2, matplotlib, scipy, numba, imutils, imageio, moviepy, kornia, timm, einops, torchmetrics, lightning, segmentation-models-pytorch, supervision, pycocotools, roboflow, label-studio-sdk, pytesseract, pyzbar, qrcode, shapely, ultralytics, albumentations, onnx, onnxruntime, pillow, scikit-image.")
        if "agents" in groups:
            lines.append("- Agents stack installed/verified: openai, anthropic, pydantic, httpx, tenacity, python-dotenv, rich, typer.")
        if "mlops" in groups:
            lines.append("- MLOps stack installed/verified: mlflow, jupyterlab, wandb, redis, psycopg.")
        if "web-dev" in groups:
            lines.extend(["- Frontend dependencies installed/verified with npm.", "- Frontend production build generated in frontend/dist.", "- Angular CLI installed/verified globally."])
        if "db" in groups or "mlops" in groups:
            lines.append("- Docker and Docker Compose verified for selected service profiles.")
        lines.extend(["- Backend compile smoke check passed.", "- Frontend build smoke check passed."])
        if "hardware-io-utils" in groups:
            lines.append("- Hardware/IO utility profile integrated: pyserial, pygame, pynput, pyautogui, pyusb, bleak, MQTT, FastAPI, Selenium/Playwright, document tooling, Streamlit/Gradio/Dash, geospatial/3D/rendering/dev tooling.")
        if "data-viz-ml-nlp-extended" in groups:
            lines.append("- Data-viz/ML/NLP extended profile integrated: matplotlib ecosystem, seaborn, cartopy, holoviews, graph libraries, stats/time-series/finance, AutoML/explainability, vector search, NLP, scraping/readability/PDF tooling.")
    else:
        lines.append("- Dry-run only. No packages were installed.")

    if state.requirement_plan:
        lines.extend(["", "Requirement planner:"])
        for item in state.requirement_plan.get("evidence", [])[:8]:
            if item.get("type") == "keyword-rule":
                matched = ", ".join(str(value) for value in item.get("matched", [])[:6])
                lines.append(f"- {item.get('id')}: {matched}")
            elif item.get("type") == "recipe":
                lines.append(f"- recipe: {item.get('id')}")

    if state.degraded:
        lines.extend(
            [
                "",
                "Degraded mode:",
                "- NVIDIA/CUDA was not enabled because nvidia-smi was not detected.",
                "- PyTorch installed/verified in CPU mode.",
            ]
        )

    lines.extend(
        [
            "",
            "Next command:",
            "./install.sh",
        ]
    )
    return lines


def write_summary(state: InstallerState, report_path: Path) -> Path:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    summary_path = LOG_ROOT / "latest-summary.txt"
    summary_path.write_text("\n".join(build_summary_lines(state, report_path)) + "\n", encoding="utf-8")
    return summary_path


def header_panel(state: InstallerState) -> Panel:
    text = Text()
    text.append(f"{LOGO}\n", style="bold magenta")
    text.append("React + Three.js + Flask + Socket.IO + ML Stack\n", style="bright_cyan")
    text.append("\nProfile: ", style="bold white")
    text.append(state.profile, style="bold yellow")
    text.append(" | Mode: ", style="bold white")
    text.append("EXECUTE" if state.execute else "DRY-RUN", style="bold green" if state.execute else "bold yellow")
    if state.allow_system:
        text.append(" | system install enabled", style="bold red")
    return Panel(Align.center(text), title="[bold cyan]HABLA Observer IA[/bold cyan]", border_style="bright_cyan", box=HEAVY)


def system_panel(state: InstallerState) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="cyan")
    table.add_column(style="white")
    for key, value in state.system.items():
        table.add_row(key, f": {value}")
    return Panel(table, title="[bold green]System Detection[/bold green]", border_style="cyan", box=ROUNDED)


def profile_panel(state: InstallerState) -> Panel:
    groups = ", ".join(resolve_groups(state))
    table = Table.grid(padding=(0, 1))
    table.add_column(style="white")
    table.add_column(style="yellow")
    table.add_row("Profile", f": {state.profile}")
    table.add_row("Description", f": {profile_description(state)}")
    table.add_row("Groups", f": {groups}")
    table.add_row("GPU", f": {state.detected_gpu}")
    table.add_row("Runtime", f": {state.mode}")
    return Panel(table, title="[bold magenta]Selected Profile[/bold magenta]", border_style="magenta", box=ROUNDED)


def steps_panel(state: InstallerState, steps: list[StepSpec]) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=8)
    table.add_column(ratio=3)
    table.add_column(width=12)
    for idx, step in enumerate(steps, start=1):
        active = idx == state.current_step + 1 and not step.done
        title_style = "bold cyan" if active else "white"
        status = "FAILED" if step.failed else "DONE" if step.done else "PENDING"
        status_style = "red" if step.failed else "green" if step.done else "yellow"
        filled = max(0, min(24, int(step.progress / 100 * 24)))
        bar = "[green]" + "#" * filled + "[/green]" + "[dim]" + "-" * (24 - filled) + "[/dim]"
        table.add_row(f"{idx:02d}. [{title_style}]{step.title}[/{title_style}]", bar, f"[{status_style}]{status}[/{status_style}]")
    return Panel(table, title="[bold blue]Installation Phases[/bold blue]", border_style="blue", box=ROUNDED)


def components_panel(state: InstallerState) -> Panel:
    table = Table.grid()
    table.add_column()
    for name, status in state.components[:28]:
        style = "green" if status not in {"missing", "degraded"} else "yellow"
        table.add_row(f"[{style}]{name}[/{style}] : {status}")
    return Panel(table, title="[bold blue]Components[/bold blue]", border_style="blue", box=ROUNDED)


def logs_panel(state: InstallerState) -> Panel:
    content = "\n".join(state.logs) if state.logs else "[dim]Waiting for installer events...[/dim]"
    return Panel(content, title="[bold cyan]Live Log[/bold cyan]", border_style="cyan", box=ROUNDED)


def progress_panel(state: InstallerState) -> Panel:
    filled = int(state.total_progress / 100 * 58)
    text = Text()
    text.append("Total progress: ", style="blue")
    text.append("[", style="white")
    text.append("=" * filled + ">", style="cyan")
    text.append(" " * max(0, 58 - filled), style="dim")
    text.append("] ", style="white")
    text.append(f"{state.total_progress:3d}%", style="bold cyan")
    if state.execute:
        text.append("\nEXECUTION MODE: project commands are allowed.", style="italic green")
        if not state.allow_system:
            text.append(" OS packages are still blocked.", style="italic yellow")
    else:
        text.append("\nDRY-RUN MODE: no packages were installed. Add --execute to install project dependencies.", style="italic yellow")
    return Panel(text, border_style="cyan", box=ROUNDED)


def make_layout(state: InstallerState, steps: list[StepSpec]) -> Layout:
    layout = Layout(name="root")
    layout.split_column(Layout(name="top", size=12), Layout(name="middle", ratio=1), Layout(name="bottom", size=5))
    layout["top"].split_row(Layout(header_panel(state), ratio=1), Layout(system_panel(state), ratio=1))
    layout["middle"].split_row(Layout(name="left", ratio=3), Layout(name="right", ratio=1))
    layout["left"].split_column(Layout(profile_panel(state), size=8), Layout(steps_panel(state, steps), ratio=2), Layout(logs_panel(state), ratio=1))
    layout["right"].update(components_panel(state))
    layout["bottom"].update(progress_panel(state))
    return layout


def run_installer(state: InstallerState, speed: float, *, screen: bool = False) -> Path:
    detect_system(state)
    state.components = build_components(state)
    steps = build_steps(state)
    add_log(state, "HABLA installer initialized")
    add_log(state, "Dry-run mode" if not state.execute else "Execution mode")
    if state.allow_system:
        add_log(state, "System package installation is enabled", ok=False)

    steps_report: list[dict[str, Any]] = []
    with Live(make_layout(state, steps), refresh_per_second=8, screen=screen, console=console) as live:
        for idx, step in enumerate(steps):
            state.current_step = idx
            step.progress = 5
            live.update(make_layout(state, steps))
            if speed:
                time.sleep(speed)
            record = run_step(state, step)
            steps_report.append(record)
            state.total_progress = int(((idx + 1) / len(steps)) * 100)
            live.update(make_layout(state, steps))
            if step.failed:
                add_log(state, f"Stopped at failed step: {step.title}", ok=False)
                break
            if speed:
                time.sleep(speed)
        state.total_progress = 100 if all(not step.failed for step in steps) else state.total_progress
        report_path = write_report(state, steps_report)
        add_log(state, f"Report written: {report_path}")
        live.update(make_layout(state, steps))
        if speed:
            time.sleep(min(1.2, max(0.2, speed * 8)))
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HABLA Observer IA automatic installer")
    parser.add_argument("--profile", default="base", choices=sorted(PROFILE_DESCRIPTIONS), help="Installation profile")
    parser.add_argument("--recipe", default="", help="Receta inteligente, por ejemplo industrial-vision, agent-platform o document-ai")
    parser.add_argument("--requirement", default="", help="Texto libre del requerimiento del cliente para calcular perfiles")
    parser.add_argument("--from-requirement", default="", help="Archivo de requerimiento del cliente para calcular perfiles")
    parser.add_argument("--ask", action="store_true", help="Mostrar caja interactiva para escribir el requerimiento del cliente")
    parser.add_argument("--execute", action="store_true", help="Run project-local installation commands")
    parser.add_argument("--allow-system", action="store_true", help="Allow OS package manager commands when --execute is enabled")
    parser.add_argument("--speed", type=float, default=0.05, help="UI animation delay")
    parser.add_argument("--screen", action="store_true", help="Use full-screen terminal mode")
    parser.add_argument("--pause", action="store_true", help="Wait for Enter before closing")
    return parser.parse_args()


def read_requirement_input(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.from_requirement:
        chunks.append(Path(args.from_requirement).read_text(encoding="utf-8"))
    if args.requirement:
        chunks.append(args.requirement)
    return "\n".join(chunk for chunk in chunks if chunk)


def recipe_names() -> list[str]:
    catalog_path = INSTALLER_ROOT / "domain_profiles.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    recipes = catalog.get("recipes") if isinstance(catalog, dict) else {}
    return sorted(recipes) if isinstance(recipes, dict) else []


def slugify_recipe(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")


def ask_for_requirement(args: argparse.Namespace) -> tuple[str, str]:
    current_requirement = read_requirement_input(args)
    current_recipe = args.recipe
    if current_requirement or current_recipe:
        return current_requirement, current_recipe

    recipes = recipe_names()
    recipe_text = ", ".join(recipes) if recipes else "industrial-vision, agent-platform, data-dashboard, full"
    console.print()
    console.print(
        Panel(
            "[bold cyan]Que necesita instalar este cliente?[/bold cyan]\n\n"
            "Escribe una descripcion normal. Ejemplos:\n"
            "- camaras USB, OpenCV, YOLO, PostgreSQL, dashboard React y sensores serial\n"
            "- agentes IA con LLM, Docker, MLflow, Redis y base de datos\n"
            "- OCR de PDF, reportes, login web y PostgreSQL\n\n"
            f"Tambien puedes escribir una receta directa: [yellow]{recipe_text}[/yellow]\n"
            "Si presionas Enter sin escribir nada, se usara la receta [yellow]full[/yellow].",
            title="[bold magenta]HABLA Installer Assistant[/bold magenta]",
            border_style="bright_cyan",
            box=ROUNDED,
        )
    )
    try:
        typed = console.input("\n[bold cyan]Requerimiento del cliente > [/bold cyan]").strip()
    except EOFError:
        typed = ""

    if not typed:
        return "", "full"

    recipe = slugify_recipe(typed)
    if recipe in recipes:
        return "", recipe
    return typed, ""


def print_requirement_plan(plan: dict[str, Any], *, execute: bool) -> None:
    groups = ", ".join(str(group) for group in plan.get("groups", []))
    evidence_lines = []
    for item in plan.get("evidence", [])[:8]:
        if item.get("type") == "recipe":
            evidence_lines.append(f"- receta: {item.get('id')}")
        elif item.get("type") == "keyword-rule":
            matched = ", ".join(str(value) for value in item.get("matched", [])[:6])
            evidence_lines.append(f"- {item.get('id')}: {matched}")
    evidence = "\n".join(evidence_lines) if evidence_lines else "- base"
    console.print()
    console.print(
        Panel(
            f"[bold]Perfil:[/bold] {plan.get('profile')}\n"
            f"[bold]Descripcion:[/bold] {plan.get('description')}\n"
            f"[bold]Grupos a instalar:[/bold] {groups}\n\n"
            f"[bold]Detectado por:[/bold]\n{evidence}",
            title="[bold green]Plan recomendado[/bold green]",
            border_style="green",
            box=ROUNDED,
        )
    )
    if execute and sys.stdin.isatty():
        proceed = Confirm.ask("Instalar este stack recomendado ahora", default=True)
        if not proceed:
            raise SystemExit(0)


def build_state_from_args(args: argparse.Namespace) -> InstallerState:
    requirement_text, recipe = ask_for_requirement(args) if args.ask else (read_requirement_input(args), args.recipe)
    if recipe or requirement_text:
        if plan_from_requirement is None:
            raise RuntimeError("requirement_planner.py no esta disponible para calcular perfiles inteligentes.")
        plan = plan_from_requirement(requirement_text, recipe=recipe)
        if args.ask:
            print_requirement_plan(plan, execute=args.execute)
        return InstallerState(
            profile=str(plan.get("profile") or "requirement-plan"),
            execute=args.execute,
            allow_system=args.allow_system,
            groups=list(plan.get("groups") or ["base"]),
            requirement_plan=plan,
        )
    return InstallerState(profile=args.profile, execute=args.execute, allow_system=args.allow_system)


def main() -> None:
    args = parse_args()
    state = build_state_from_args(args)
    try:
        report_path = run_installer(state, args.speed, screen=args.screen)
        summary_path = write_summary(state, report_path)
        console.print()
        if not args.execute:
            console.print("[bold yellow]HABLA installer dry-run completed. No packages were installed.[/bold yellow]")
        else:
            console.print("[bold green]HABLA installer finished.[/bold green]" if state.total_progress == 100 else "[bold yellow]HABLA installer stopped.[/bold yellow]")
        console.print(f"[cyan]Report:[/cyan] {report_path}")
        console.print(f"[cyan]Summary:[/cyan] {summary_path}")
        console.print()
        for line in build_summary_lines(state, report_path):
            if line.startswith("- "):
                console.print(f"[green]{line}[/green]")
            elif line.endswith(":"):
                console.print(f"[bold cyan]{line}[/bold cyan]")
            else:
                console.print(line)
        if not args.execute:
            console.print("[yellow]Dry-run only. Re-run with --execute to apply project-local commands.[/yellow]")
        if args.execute and not args.allow_system:
            console.print("[yellow]System packages were skipped. Add --allow-system only when you want OS-level installs.[/yellow]")
    finally:
        if args.pause:
            try:
                input("\nPresiona Enter para cerrar el instalador...")
            except EOFError:
                pass


if __name__ == "__main__":
    main()
