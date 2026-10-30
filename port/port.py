#!/usr/bin/env python3
"""Port Claude-Code-Game-Studios (.claude tree) into OpenCode global config.

Run:  python port/port.py          (from anywhere; paths are relative to this repo)
Source: this repository (.claude tree). Override with CCGS_SRC.
Target: ~/.config/opencode. Override with CCGS_TARGET.
  skills/<id>/SKILL.md   <- .claude/skills/<id>/
  agents/<id>.md         <- .claude/agents/<id>.md   (V2 frontmatter)
  commands/<id>.md       <- generated from each skill
  ccgs/                  <- support tree (docs, scripts, hooks, rules, templates)
Also: merges .claude/settings.json allow/deny rules into opencode.jsonc
permissions, appends a usage section to AGENTS.md, and (Windows) creates a
bash.cmd shim when git-bash is not on PATH.

Idempotent: safe to re-run after `git pull` (updates flow straight through).
Requires: Python 3 (PyYAML for frontmatter round-trip), Git for Windows on Windows.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
# Defaults: source = this repository (parent of port/), target = OpenCode
# global config. Override with CCGS_SRC / CCGS_TARGET env vars when needed.
REPO = Path(__file__).resolve().parent.parent
SRC = Path(os.environ.get("CCGS_SRC", REPO))
SRC_CLAUDE = SRC / ".claude"
OC = Path(os.environ.get("CCGS_TARGET", HOME / ".config" / "opencode"))
CCGS = OC / "ccgs"
CCGS_ABS = CCGS.as_posix()          # forward slashes for bash on Windows


def find_git_bash():
    for c in (shutil.which("bash"),
              r"C:\Program Files\Git\bin\bash.exe",
              r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if c and Path(c).exists():
            return Path(c)
    return None


GIT_BASH = find_git_bash()

TEXT_EXT = {".md", ".sh", ".py", ".awk", ".gd", ".json", ".jsonc",
            ".yaml", ".yml", ".txt", ".cfg", ".toml", ".cmd", ".ps1"}
FRONT_DROP = {"allowed-tools", "argument-hint", "user-invocable", "model",
              "maxTurns", "memory", "disallowedTools", "tools"}

stats = {"skills": 0, "agents": 0, "commands": 0, "ccgs_files": 0}


def log(msg):
    print(msg, flush=True)


def split_fm(text):
    """Return (frontmatter_lines_or_None, body)."""
    if text.startswith("---"):
        lines = text.splitlines()
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], "\n".join(lines[i + 1:]).lstrip("\n")
    return None, text


def rewrite(s):
    """Claude-Code-isms -> OpenCode/absolute-path equivalents."""
    s = s.replace("$CLAUDE_PROJECT_DIR/.claude", CCGS_ABS)
    s = s.replace("$CLAUDE_PROJECT_DIR", ".")
    s = s.replace(".claude/", CCGS_ABS + "/")
    s = s.replace("`AskUserQuestion`", "the `question` tool")
    s = s.replace("AskUserQuestion", "the question tool")
    s = re.sub(r"subagent_type:\s*([A-Za-z0-9_-]+)", r"the `\1` subagent", s)
    return s


def fm_lines_to_dict(lines):
    import yaml
    return yaml.safe_load("\n".join(lines)) or {}


def convert_skill(text):
    """Keep name/description; drop Claude-only keys; rewrite body."""
    import yaml
    fm, body = split_fm(text)
    if fm is None:
        return rewrite(text), None
    d = fm_lines_to_dict(fm)
    keep = {k: d[k] for k in ("name", "description") if d.get(k)}
    fm_text = yaml.safe_dump(keep, allow_unicode=True, sort_keys=False,
                             width=10**6).rstrip()
    desc = keep.get("description", "")
    return "---\n" + fm_text + "\n---\n\n" + rewrite(body), desc


def yaml_quote(v):
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def convert_agent(text, agent_id):
    """Claude agent frontmatter -> OpenCode V2 agent frontmatter."""
    import yaml
    fm, body = split_fm(text)
    if fm is None:
        raise SystemExit(f"agent {agent_id}: no frontmatter")
    d = fm_lines_to_dict(fm)
    tools = set()
    t = d.get("tools")
    if isinstance(t, str):
        tools = {x.strip() for x in t.split(",") if x.strip()}
    elif isinstance(t, list):
        tools = set(t)
    for x in (d.get("disallowedTools") or []):
        tools.discard(x)
    perms = []
    if not (tools & {"Write", "Edit", "NotebookEdit"}):
        perms.append(("edit", "*", "deny"))
    if "Bash" not in tools:
        perms.append(("shell", "*", "deny"))
    if "WebSearch" not in tools:
        perms.append(("websearch", "*", "deny"))
    if "WebFetch" not in tools:
        perms.append(("webfetch", "*", "deny"))
    head = ["---", "description: " + yaml_quote(str(d.get("description", "")).strip()),
            "mode: subagent"]
    if perms:
        head.append("permissions:")
        for a, r, e in perms:
            head += [f"  - action: {a}", f'    resource: "{r}"', f"    effect: {e}"]
    mt = d.get("maxTurns")
    if isinstance(mt, int):
        head.append(f"steps: {mt}")
    head.append("---")
    return "\n".join(head) + "\n\n" + rewrite(body.strip()) + "\n"


def copy_text_file(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        src.read_text(encoding="utf-8")
        txt = src.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        shutil.copy2(src, dst)
        return
    dst.write_text(rewrite(txt), encoding="utf-8", newline="\n")


def install_skills():
    """Copy each skill dir; strip Claude frontmatter keys; rewrite paths."""
    skill_descs = {}
    src_root = SRC_CLAUDE / "skills"
    for d in sorted(p for p in src_root.iterdir() if p.is_dir()):
        sid = d.name
        dest = OC / "skills" / sid
        if dest.exists():
            shutil.rmtree(dest)
        desc = None
        for f in sorted(d.rglob("*")):
            if f.is_dir():
                continue
            rel = f.relative_to(d)
            target = dest / rel
            if f.suffix == ".md":
                target.parent.mkdir(parents=True, exist_ok=True)
                res, res_desc = convert_skill(f.read_text(encoding="utf-8"))
                if f.name == "SKILL.md":
                    desc = res_desc
                target.write_text(res, encoding="utf-8", newline="\n")
            else:
                copy_text_file(f, target)
        if not desc:
            desc = "Claude Code Game Studios skill: " + sid
        skill_descs[sid] = desc
        stats["skills"] += 1
    return skill_descs


def install_agents():
    src_root = SRC_CLAUDE / "agents"
    dest_root = OC / "agents"
    dest_root.mkdir(parents=True, exist_ok=True)
    for f in sorted(src_root.glob("*.md")):
        aid = f.stem
        text = f.read_text(encoding="utf-8")
        (dest_root / f"{aid}.md").write_text(
            convert_agent(text, aid), encoding="utf-8", newline="\n")
        stats["agents"] += 1


def install_support_tree():
    """docs/, scripts/, hooks/, rules/, templates -> OC/ccgs/ (rewritten)."""
    if CCGS.exists():
        shutil.rmtree(CCGS)
    CCGS.mkdir(parents=True)
    n = 0
    for name in ("docs", "scripts", "hooks", "rules"):
        s = SRC_CLAUDE / name
        if not s.exists():
            continue
        for f in sorted(s.rglob("*")):
            if f.is_dir():
                continue
            copy_text_file(f, CCGS / name / f.relative_to(s))
            n += 1
    for extra in ("settings.json",):
        s = SRC_CLAUDE / extra
        if s.exists():
            copy_text_file(s, CCGS / extra)
            n += 1
    shutil.copy2(SRC / "project.yaml", CCGS / "project.template.yaml")
    shutil.copy2(SRC / "CLAUDE.md", CCGS / "studio-reference.md")
    add_port_note(CCGS / "docs" / "config-resolution.md")
    stats["ccgs_files"] = n


PORT_NOTE = """

---

## OpenCode port note

This framework was ported from Claude Code (Donchitos/Claude-Code-Game-Studios
v1.2.0) to OpenCode. The Claude-specific environment variables documented above
(`CLAUDE_PROJECT_DIR`, `CLAUDE_SKILL_DIR`) do not exist in OpenCode: the port
rewrote `.claude/` references to absolute paths under
`{ccgs}/`, and project-relative paths resolve from the current working
directory. Claude-only features (settings.json hooks, path-scoped rules,
statusline) are not ported - see the repository README.
""".replace("{ccgs}", CCGS_ABS)


def add_port_note(path):
    if not path.exists():
        return
    t = path.read_text(encoding="utf-8")
    if "OpenCode port note" in t:
        t = re.sub(r"\n*---\n\n## OpenCode port note.*$", PORT_NOTE.strip("\n"),
                   t, flags=re.S)
    else:
        t = t.rstrip("\n") + "\n" + PORT_NOTE.strip("\n")
    path.write_text(t, encoding="utf-8", newline="\n")


def install_commands(skill_descs):
    """One /<skill-id> command per skill, mirroring Claude slash commands."""
    dest_root = OC / "commands"
    dest_root.mkdir(parents=True, exist_ok=True)
    for sid, desc in skill_descs.items():
        short = re.split(r"(?<=[.!?])\s", desc)[0][:120] or sid
        body = (f"Load and follow the studio skill `{sid}` "
                f"(Claude Code Game Studios) for this request: $ARGUMENTS\n")
        text = ("---\ndescription: " + yaml_quote(short) +
                "\n---\n\n" + body)
        (dest_root / f"{sid}.md").write_text(text, encoding="utf-8", newline="\n")
        stats["commands"] += 1


ACTION_MAP = {"Bash": "shell", "PowerShell": "shell",
              "Read": "read", "Edit": "edit"}


def norm_resource(r):
    r = re.sub(r"^\*\*/", "", r)        # **/.env*  -> .env*
    r = re.sub(r"^\*\*/\*/", "*/", r)   # **/*.uasset -> *.uasset
    return r


def port_permissions():
    """Merge .claude/settings.json allow/deny into opencode.jsonc permissions."""
    s = json.loads((SRC_CLAUDE / "settings.json").read_text(encoding="utf-8"))
    perms = s.get("permissions", {})
    rules, seen = [], set()
    for effect in ("allow", "deny"):
        for entry in perms.get(effect, []):
            m = re.match(r"^(Bash|PowerShell|Read|Edit)\((.*)\)$", entry)
            if not m:
                continue
            action = ACTION_MAP[m.group(1)]
            resource = norm_resource(m.group(2).strip())
            key = (action, resource)
            if key in seen:
                continue
            seen.add(key)
            rules.append({"action": action, "resource": resource,
                          "effect": effect})
    cfg_path = OC / "opencode.jsonc"
    raw = cfg_path.read_text(encoding="utf-8")
    if '"permissions"' in raw:
        log("  ! opencode.jsonc already has permissions - skipped (edit by hand)")
        return rules
    lines = ["  // --- Claude Code Game Studios: ported from .claude/settings.json ---",
             '  "permissions": [']
    for i, r in enumerate(rules):
        lines.append('    { "action": "%s", "resource": %s, "effect": "%s" }%s'
                     % (r["action"], json.dumps(r["resource"]), r["effect"],
                        "," if i < len(rules) - 1 else ""))
    lines.append("  ],")
    block = "\n".join(lines) + "\n"
    marker = '  "mcp": {'
    if marker not in raw:
        raise SystemExit("cannot find \"mcp\" anchor in opencode.jsonc")
    cfg_path.write_text(raw.replace(marker, block + marker, 1),
                        encoding="utf-8", newline="\n")
    return rules


def update_agents_md():
    """Append a CCGS section to the global AGENTS.md (idempotent)."""
    p = OC / "AGENTS.md"
    raw = p.read_text(encoding="utf-8") if p.exists() else ""
    marker = "## Claude Code Game Studios"
    if marker in raw:
        raw = raw[:raw.index(marker)].rstrip() + "\n"
    section = f"""

{marker} (ported from Donchitos/Claude-Code-Game-Studios v1.2.0)

Installed globally into this OpenCode config on {os.environ.get('PORT_DATE','')}.

- **74 skills** - load with the `skill` tool by ID (e.g. `start`, `brainstorm`,
  `design-system`, `dev-story`) or run them as slash commands: `/start`, `/brainstorm`, ...
- **49 subagents** - launch by name via the subagent tool: `creative-director`,
  `technical-director`, `producer`, `game-designer`, `gameplay-programmer`, ...
- **Support tree** (bash helpers, docs, rules, hooks, templates):
  `{CCGS_ABS}/`
- **Per-project config**: each game project needs its own `project.yaml` at the
  project root - run `/adopt` in an existing project or `/start` in a new folder.
- **Bash required**: studio helpers are bash scripts; install Git for Windows on
  Windows. The port creates a `bash.cmd` shim on PATH when `bash` is missing, so
  skills can keep calling `bash <script>` unchanged.
- **Hooks are NOT ported** (Claude Code-only feature). The safety net is the
  deny rules ported into `opencode.jsonc` (rm -rf, git push --force, .env, ...).
- **Collaboration protocol**: Question -> Options -> Decision -> Draft -> Approval.
- **Upstream updates**: `git -C "{SRC}" pull` then rerun the port script at
  `{CCGS_ABS}/port.py`.

"""
    p.write_text(raw + section, encoding="utf-8", newline="\n")


def ensure_bash_shim():
    """Make `bash` resolvable from any shell (Git for Windows bin is not on PATH).

    Creates a tiny bash.cmd wrapper in the first writable PATH directory.
    Skipped when bash is already reachable or Git for Windows is absent.
    """
    if shutil.which("bash"):
        log("  bash already on PATH - shim skipped")
        return None
    if not GIT_BASH or not GIT_BASH.exists():
        log("  ! Git for Windows bash not found - shim skipped "
            "(install Git for Windows or add bash to PATH)")
        return None
    candidates = [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep)
                  if p]
    shim_dir = next((d for d in candidates if d.is_dir() and os.access(d, os.W_OK)),
                    None)
    if shim_dir is None:
        shim_dir = HOME / ".local" / "bin"
        shim_dir.mkdir(parents=True, exist_ok=True)
    shim = shim_dir / "bash.cmd"
    shim.write_text(f'@echo off\r\n"{GIT_BASH}" %*\r\n',
                    encoding="ascii", newline="\r\n")
    log(f"  bash shim -> {shim}")
    return shim


def verify():
    import yaml
    problems = []
    for f in sorted((OC / "agents").glob("*.md")):
        fm, _ = split_fm(f.read_text(encoding="utf-8"))
        if fm is None:
            problems.append(f"{f.name}: no frontmatter"); continue
        try:
            d = fm_lines_to_dict(fm)
            assert d.get("description") and d.get("mode") == "subagent"
        except Exception as e:
            problems.append(f"{f.name}: {e}")
    leftover = []
    for f in list(OC.rglob("*.md")) + list(CCGS.rglob("*.sh")):
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if ".claude/" in t or "AskUserQuestion" in t or "CLAUDE_PROJECT_DIR" in t:
            leftover.append(str(f.relative_to(OC)))
    return problems, leftover


def main():
    import datetime
    os.environ["PORT_DATE"] = datetime.date.today().isoformat()
    log(f"source: {SRC_CLAUDE}")
    log(f"target: {OC}")
    log(f"ccgs:   {CCGS_ABS}")
    skill_descs = install_skills()
    install_agents()
    install_support_tree()
    install_commands(skill_descs)
    log("porting permissions from settings.json ...")
    rules = port_permissions()
    ensure_bash_shim()
    update_agents_md()
    problems, leftover = verify()
    log(f"\nDONE  skills={stats['skills']} agents={stats['agents']} "
        f"commands={stats['commands']} ccgs_files={stats['ccgs_files']} "
        f"permission_rules={len(rules)}")
    log(f"frontmatter problems: {len(problems)}")
    for p in problems[:10]:
        log("  ! " + p)
    log(f"files still containing Claude-isms: {len(leftover)}")
    for p in leftover[:10]:
        log("  ! " + p)
    shutil.copy2(__file__, CCGS / "port.py")
    log(f"port script saved -> {CCGS_ABS}/port.py")


if __name__ == "__main__":
    main()
