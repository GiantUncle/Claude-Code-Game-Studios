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


_SKILL_DIR_ABS = None   # set per-skill in install_skills()


def rewrite(s):
    """Claude-Code-isms -> OpenCode/absolute-path equivalents.

    Handles every shell form of the two env vars Claude Code injects:
      $CLAUDE_PROJECT_DIR  ${CLAUDE_PROJECT_DIR}  ${CLAUDE_PROJECT_DIR%/}
      ${CLAUDE_PROJECT_DIR:-}  ${CLAUDE_PROJECT_DIR:-.}   (+ optional /.claude)
      $CLAUDE_SKILL_DIR    ${CLAUDE_SKILL_DIR}
      ${CLAUDE_SKILL_DIR}/../../  (skill dir -> ccgs root)
    """
    # 1) skill dir: "/../../" variant points at the ccgs root (hooks/, scripts/)
    s = re.sub(r"\$\{(CLAUDE_SKILL_DIR)[^}]*\}/\.\./\.\./", CCGS_ABS + "/", s)
    s = re.sub(r"\$(CLAUDE_SKILL_DIR)/\.\./\.\./", CCGS_ABS + "/", s)
    # 2) bare skill-dir var -> this skill's installed dir (or cwd outside skills).
    #    Braced form may carry a default ("${CLAUDE_SKILL_DIR:-x}"); the
    #    unbraced form must NOT swallow trailing punctuation - see the
    #    "$VAR\" ... :" corruption fixed in 1.2.1 (no [^}]* outside braces).
    s = re.sub(r"\$\{CLAUDE_SKILL_DIR[^}]*\}", _SKILL_DIR_ABS or ".", s)
    s = re.sub(r"\$CLAUDE_SKILL_DIR\b", _SKILL_DIR_ABS or ".", s)
    # 3) project-dir var; keep a trailing "/.claude" folded into the ccgs root.
    #    Braced forms first (they may carry defaults/modifiers), then bare.
    s = re.sub(r"\$\{CLAUDE_PROJECT_DIR[^}]*\}(/\.claude)?",
               lambda m: CCGS_ABS if m.group(1) else ".", s)
    s = re.sub(r"\$CLAUDE_PROJECT_DIR\b(/\.claude)?",
               lambda m: CCGS_ABS if m.group(1) else ".", s)
    # 4) bare .claude/ references -> ccgs root
    s = s.replace(".claude/", CCGS_ABS + "/")
    # 5) Claude tool names -> OpenCode equivalents / neutral phrasing
    s = s.replace("`AskUserQuestion`", "the `question` tool")
    s = s.replace("AskUserQuestion", "the question tool")
    # 5b) Claude reads project instructions from CLAUDE.md, OpenCode reads
    #     AGENTS.md. Skills that edit or verify CLAUDE.md would otherwise
    #     write a file OpenCode never loads. Longest form first.
    s = s.replace("CLAUDE.local.md", "AGENTS.md")
    s = s.replace("CLAUDE.md", "AGENTS.md")
    s = s.replace("4-claude-md-stack", "4-agents-md-stack")
    # Claude Task-tool vocabulary -> OpenCode subagent phrasing.
    # Bracketed placeholders ("subagent_type: [engine specialist]") first, then
    # concrete agent ids ("subagent_type: release-manager").
    s = re.sub(r"subagent_type:\s*\[([^\]]+)\]", r"subagent: <\1>", s)
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
    keep = {k: rewrite(d[k]) for k in ("name", "description") if d.get(k)}
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
    head = ["---",
            "description: " + yaml_quote(rewrite(str(d.get("description", "")).strip())),
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
    global _SKILL_DIR_ABS
    skill_descs = {}
    src_root = SRC_CLAUDE / "skills"
    for d in sorted(p for p in src_root.iterdir() if p.is_dir()):
        sid = d.name
        dest = OC / "skills" / sid
        _SKILL_DIR_ABS = dest.as_posix()   # for ${CLAUDE_SKILL_DIR} rewriting
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
            # reference files named after Claude concepts follow the rename
            if "claude" in target.name.lower() and target.name != "SKILL.md":
                renamed = target.with_name(
                    target.name.lower().replace("claude", "agents"))
                target.rename(renamed)
        if not desc:
            desc = "Claude Code Game Studios skill: " + sid
        skill_descs[sid] = desc
        stats["skills"] += 1
    _SKILL_DIR_ABS = None
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
            dst = CCGS / name / f.relative_to(s)
            copy_text_file(f, dst)
            if f.suffix == ".sh":
                patch_root_anchors(dst)
            n += 1
    yh = CCGS / "hooks" / "yaml-helper.sh"
    if yh.exists():
        n += patch_yaml_helper(yh)
    for extra in ("settings.json",):
        s = SRC_CLAUDE / extra
        if s.exists():
            copy_text_file(s, CCGS / extra)
            n += 1
    shutil.copy2(SRC / "project.yaml", CCGS / "project.template.yaml")
    # the framework's own instruction file: kept verbatim for provenance, and
    # under AGENTS.md so rewritten doc references (CLAUDE.md -> AGENTS.md) still
    # resolve inside the support tree
    shutil.copy2(SRC / "CLAUDE.md", CCGS / "studio-reference.md")
    shutil.copy2(SRC / "CLAUDE.md", CCGS / "AGENTS.md")
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


_ROOT_ANCHOR_SUBS = [
    # statement form -> resolve from the invocation directory, walking up to the
    # nearest project.yaml (upstream: the script lived inside the project repo)
    ('cd "$HERE/../.."', 'cd "$(ccgs_project_root)"'),
    ('cd "$(dirname "$0")/../.."', 'cd "$(ccgs_project_root)"'),
    ('cd "$(dirname "${BASH_SOURCE[0]}")/../.."', 'cd "$(ccgs_project_root)"'),
    # assignment form -> same resolver
    ('"$(cd "$(dirname "$0")/../.." && pwd)"', '"$(ccgs_project_root)"'),
]

# Injected after the shebang of every patched script. Mirrors the upward search
# patched into yaml-helper.sh: project root = cwd if it holds project.yaml,
# else the nearest ancestor that does, else cwd. Terminates on every platform
# (guards against fixed points like "." and "/").
_ROOT_FN = '''ccgs_project_root() {  # [port] project root = nearest project.yaml above cwd
  ccgs_d="${PWD}"
  while [ -n "$ccgs_d" ] && [ "$ccgs_d" != "/" ] && [ "$ccgs_d" != "." ]; do
    if [ -f "$ccgs_d/project.yaml" ]; then
      cd "$ccgs_d" 2>/dev/null && { pwd -W 2>/dev/null || pwd; return 0; }
      printf '%s\\n' "$ccgs_d"; return 0
    fi
    ccgs_n="$(dirname "$ccgs_d")"
    [ "$ccgs_n" = "$ccgs_d" ] && break
    ccgs_d="$ccgs_n"
  done
  pwd -W 2>/dev/null || pwd
}
'''


def patch_root_anchors(path):
    """Scripts assume `<script>/../..` is the project root - true when the
    framework ships inside the project repo (upstream layout), false after a
    global install, where it points at ~/.config/opencode. Redirect the anchor
    to a resolver over the invocation directory, and inject the resolver after
    the shebang. CCGS_ROOT assignments (framework-tree lookups) are left alone.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = 0
    for i, ln in enumerate(lines):
        if "CCGS_ROOT=" in ln:
            continue
        for old, new in _ROOT_ANCHOR_SUBS:
            if old in ln:
                lines[i] = ln = ln.replace(old, new)
                changed += 1
    if not changed:
        return 0
    if not any("ccgs_project_root()" in x for x in lines):
        at = 1 if lines and lines[0].startswith("#!") else 0
        lines[at:at] = _ROOT_FN.rstrip("\n").split("\n")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return changed


def patch_yaml_helper(path):
    """Replace yaml-helper's self-root fallback (framework location was the
    anchor upstream) with an upward search for project.yaml from the launch
    directory - the OpenCode equivalent of 'an anchor that cannot drift'.
    """
    t = path.read_text(encoding="utf-8")
    search = (
        '  _yh_start="${PWD}"\n'
        '  while [ -n "$_yh_start" ] && [ "$_yh_start" != "/" ] && '
        '[ "$_yh_start" != "." ]; do\n'
        '    if [ -f "$_yh_start/project.yaml" ]; then\n'
        '      CLAUDE_PROJECT_DIR="$_yh_start"\n'
        '      cd "$_yh_start" 2>/dev/null\n'
        '      break\n'
        '    fi\n'
        '    _yh_next="$(dirname "$_yh_start")"\n'
        '    [ "$_yh_next" = "$_yh_start" ] && break\n'
        '    _yh_start="$_yh_next"\n'
        '  done\n')
    a_old = ('      if [ -z "." ] || [ ! -f "./project.yaml" ]; then\n'
             '        _yh_self_root=$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)\n'
             '        [ -n "$_yh_self_root" ] && CLAUDE_PROJECT_DIR="$_yh_self_root"\n'
             '      fi\n')
    a_new = ('      # [port] upward search: the helpers no longer live inside the\n'
             '      # project repo, so the script-location anchor is meaningless.\n'
             + search)
    b_old = ('      _yh_self_root=$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)\n'
             '      if [ -z "$_yh_self_root" ] || ! cd "$_yh_self_root"; then\n'
             '        echo "yaml-helper.sh: cannot find the project root from $0" >&2\n'
             '        exit 2\n'
             '      fi\n')
    b_new = ('      # [port] upward search, same as the resolve_config branch above.\n'
             + search)
    n = 0
    if a_old in t:
        t = t.replace(a_old, a_new)
        n += 1
    if b_old in t:
        t = t.replace(b_old, b_new)
        n += 1
    if n:
        path.write_text(t, encoding="utf-8", newline="\n")
    return n


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
- **Project root**: helpers resolve it from the invocation directory, walking up
  to the nearest `project.yaml` (run commands from your game folder).
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
