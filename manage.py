import os
import subprocess
from pathlib import Path
import typer

app = typer.Typer(help="CLI del Proyecto_De_Graduacion")
ROOT = Path(__file__).parent.resolve()

def run(cmd):
    print("$ " + " ".join(cmd))
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        raise SystemExit(res.returncode)

def env_bin(exe):
    return str(ROOT / "venv" / ("Scripts" if os.name == "nt" else "bin") / exe)

def _tests_ui(base_url: str, headless: bool, browser: str):
    os.environ["BASE_URL"] = base_url
    os.environ["HEADLESS"] = "true" if headless else "false"
    os.environ["BROWSER"]  = browser
    robot = env_bin("robot")
    if not Path(robot).exists():
        robot = "robot"
    run([robot, "-d", "reports/ui", "tests-ui"])

@app.command(name="tests-ui")
def tests_ui_dash_cmd(
    base_url: str = "http://localhost:5000",
    headless: bool = True,
    browser: str = "chrome",
):
    _tests_ui(base_url, headless, browser)

if __name__ == "__main__":
    app()
