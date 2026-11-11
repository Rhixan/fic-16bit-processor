"""Assemble a program, build the CPU, run headlessly, print the final
register state (last changed row of the -t table + halt run)."""
import sys, subprocess, os
from assembler import assemble
from build_cpu import build_cpu
from circ_builder import render_project

def _find_jar():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "logisim.jar"),
                 os.path.join(here, "..", "gen", "logisim.jar"),
                 os.path.join(here, "..", "logisim.jar")):
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return os.environ.get("LOGISIM_JAR", "logisim.jar")

JAR = _find_jar()
JOPTS = ["-Djava.awt.headless=true", "-Djava.util.prefs.userRoot=/tmp/juser",
         "-Djava.util.prefs.systemRoot=/tmp/juser"]


def run(asm_path, max_seconds=25):
    prog = assemble(open(asm_path).read())
    circ = build_cpu(prog)
    import tempfile
    out = os.path.join(tempfile.gettempdir(), "_fic_run.circ")
    open(out, "w").write(render_project([circ]))
    cmd = ["java"] + JOPTS + ["-jar", JAR, "-t", "table", "-t", "halt", out]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_seconds)
        txt = p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        txt = (e.stdout or b"").decode() + "\n[TIMEOUT - did not halt]"
    rows = []
    halted = "halt pin" in txt
    for line in txt.splitlines():
        s = line.strip()
        if s and (s[0] in "01"):
            rows.append(s)
    labels = ["A", "X", "Y", "PC", "SP", "FLAG"]
    print(f"=== {asm_path} === ({'HALTED' if halted else 'NOT halted'})")
    if rows:
        last = rows[-1].split("\t")
        for lbl, val in zip(labels, last):
            v = val.replace(" ", "")
            try:
                iv = int(v, 2)
                print(f"  {lbl:5} = 0x{iv:04X} ({iv})")
            except ValueError:
                print(f"  {lbl:5} = {val}")
    return rows, halted


if __name__ == "__main__":
    for path in sys.argv[1:]:
        run(path)
        print()
