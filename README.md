<p align="center">
  <strong>⚠️ 이 저장소는 <a href="https://github.com/Donchitos/Claude-Code-Game-Studios">원본</a>의
  포크로, <a href="https://opencode.ai">OpenCode</a>용 포팅이 적용되어 있습니다.
  포팅 설명과 사용법은 <a href="#-opencode-포팅-버전--이-저장소에-대해">바로 아래</a>에 있습니다.</strong>
</p>

---

# 🇰🇷 OpenCode 포팅 버전 — 이 저장소에 대해

> 이 저장소는 [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)
> v1.2.0(MIT)을 **OpenCode에서 사용할 수 있도록 포팅한 포크**입니다. 원본의
> 저작권·라이선스(MIT)와 크레딧은 그대로 유지됩니다.
>
> 원본은 **Anthropic Claude Code(CLI) 전용** 프로젝트입니다. Claude Code 없이
> **OpenCode**만 쓰는 경우를 위해, 원본의 "게임 스튜디오 조직도와 워크플로"라는
> **콘텐츠는 그대로 두고, OpenCode가 이해하는 형태로 배선만 다시 연결**했습니다.

**English summary:** this fork ports the upstream *Claude Code*-only framework
to [OpenCode](https://opencode.ai) V2. The studio content (49 agents, 74
workflow skills, templates, bash helpers) ships unchanged; `port/port.py`
converts the wiring — skills, agents, slash commands, permissions, project-root
resolution and instruction-file targets — into OpenCode's formats and installs
them globally. Claude-only features (settings hooks, statusline, path-scoped
rules) are intentionally not ported; they are listed below with workarounds.

## 목차

- 한눈에 보기
- 포팅 방식 — 무엇을 어떻게 바꿨나
- 설치 방법
- 설치 후 사용법
- 이식된 것 / 이식되지 않은 것
- 알려진 제약
- 검증 결과
- 포트 수정 이력
- 업데이트 / 제거
- 크레딧

### 한눈에 보기

| 항목 | 내용 |
|---|---|
| 원본 | Donchitos/Claude-Code-Game-Studios v1.2.0 (commit `05ad7c8`, MIT) |
| 포팅 대상 도구 | [OpenCode](https://opencode.ai) V2 |
| 포팅 도구 | `port/port.py` v1.2.2 (Python 3, 멱등 재실행 가능) |
| 설치 위치 | OpenCode 전역 설정 `~/.config/opencode/` |
| 실제 이식 규모 | 스킬 74개 · 서브에이전트 49개 · 슬래시 커맨드 74개 · 지원 스크립트/문서 198개 · 권한 규칙 84개 |

### 포팅 방식 — 무엇을 어떻게 바꿨나

원본 구조 → OpenCode 구조로 **기계 변환**합니다(손으로 옮기지 않음).

| 원본 (Claude Code용) | 포팅 결과 (OpenCode용) | 변환 내용 |
|---|---|---|
| `.claude/skills/<id>/SKILL.md` | `~/.config/opencode/skills/<id>/SKILL.md` | 형식이 사실상 동일. Claude 전용 frontmatter 키(`allowed-tools`, `argument-hint`, `user-invocable`, `model`) 제거, 본문의 `.claude/` 경로 751곳을 절대경로로 치환, `AskUserQuestion` → `question` 도구 표현으로 교체 |
| `.claude/agents/<id>.md` | `~/.config/opencode/agents/<id>.md` | frontmatter를 OpenCode V2 스키마로 변환: `tools:` 목록 → `permissions` 규칙(deny), `maxTurns` → `steps`, `model: opus/sonnet` 제거(세션 모델 **상속**), `memory` 제거. 에이전트 이름은 그대로라 `subagent` 도구가 이름으로 호출 가능 |
| 스킬 = Claude 슬래시 커맨드 | `~/.config/opencode/commands/<id>.md` | 스킬 74개를 `/start`, `/brainstorm` 같은 슬래시 커맨드로 **자동 생성** |
| `.claude/settings.json`의 allow/deny 목록 | `opencode.jsonc`의 `permissions` | `Bash(...)` → `shell` 액션 등으로 변환 후 전역 규칙에 병합(`rm -rf`, `git push --force`, `.env` 읽기 등 차단) |
| `CLAUDE.md` (프로젝트 지시 파일) | `AGENTS.md` | OpenCode는 프로젝트 지시를 `AGENTS.md`에서 읽는다. 본문·frontmatter·파일명(`4-claude-md-stack.md` → `4-agents-md-stack.md`)까지 전부 치환 — `/setup-engine` 등이 CLAUDE.md를 편집하던 동작이 AGENTS.md로 가지 않게 하기 위함 |
| `.claude/`의 scripts·docs·rules·templates | `~/.config/opencode/ccgs/` | bash 헬퍼 35개 포함 전체 보관, 경로 치환만 수행 |
| `project.yaml` | 그대로 사용 | 프로젝트 루트의 설정 파일 형식은 양쪽 도구 무관. PyYAML 불필요(스킬이 bash 헬퍼로 읽음) |

### 설치 방법

**요구사항**: Git, Python 3, OpenCode, Windows라면 Git for Windows(bash).

```bash
# 1) 이 저장소 클론
git clone https://github.com/<your-id>/Claude-Code-Game-Studios.git
cd Claude-Code-Game-Studios

# 2) 원본 내용이 이 폴더 안에 그대로 있으므로, 포트 스크립트 실행
python port/port.py
```

실행 시 `~/.config/opencode/` 아래에 skills / agents / commands / ccgs가
생성되고, `opencode.jsonc`에 권한 규칙이 병합되며, 전역 `AGENTS.md`에 사용법
섹션이 추가됩니다. **멱등**이므로 여러 번 실행해도 안전하며, 원본을
`git pull`로 업데이트한 뒤 다시 실행하면 변경분이 그대로 반영됩니다.

동시에 Claude Code 쪽 배선(`.claude/` 원본 트리)은 그대로 유지되므로, 이
저장소는 **한 폴더에서 Claude Code와 OpenCode를 모두 지원**합니다.

### 설치 후 사용법

- **슬래시 커맨드**: `/start`(온보딩), `/brainstorm`, `/design-system`,
  `/dev-story`, `/gate-check` 등 — 원본과 동일한 이름으로 사용
- **스킬 직접 로드**: OpenCode의 `skill` 도구에 `start`, `dev-story` 등 ID 지정
- **스튜디오 팀 호출**: "creative-director 에이전트로 검토해줘"처럼 이름으로
  서브에이전트 호출(이사 3 · 부서장 8 · 전문가 38)
- **프로젝트 적용**: 게임 폴더에서 `/adopt`(기존 프로젝트) 또는 `/start`(신규)
  실행 → 해당 폴더에 `project.yaml` 생성. 스킬들은 프로젝트를 인식하고
  design/ · production/ · docs/ 산출물을 관리
- **주의**: 스킬 내부는 bash 헬퍼를 호출하므로 `bash`가 필요합니다. Windows에서
  PATH에 bash가 없으면 포트 스크립트가 자동으로 `bash.cmd` 심을 만들어 줍니다.

### ✅ 이식된 것 / ❌ 이식되지 않은 것

**이식됨**

- 스킬 74개(내용·워크플로 전부) — `question` 도구 표현만 OpenCode식으로 조정
- 서브에이전트 49개(이름·시스템 프롬프트 전부, 권한/스텝 제한 포함)
- 슬래시 커맨드 74개
- settings.json 권한 규칙 84개(안전망: `rm -rf` · `git push --force` ·
  `git reset --hard` · `.env`/`.uasset`/`.umap` 편집 차단 등)
- bash 헬퍼 스크립트 35개, 문서/룰/템플릿 전체 보관
- 전역 `AGENTS.md`에 포팅 사용법 섹션(멱등)

**이식되지 않음 — Claude Code 전용 기능**

| 기능 | 원본에서의 역할 | 미이식 사유 / 현재 상태 |
|---|---|---|
| `settings.json` 훅 15개 | PreToolUse/PostToolUse/SessionStart 등 8종 이벤트에서 커밋·푸시·에셋·문서 변경 자동 검증 | OpenCode에 대응 기능 없음. 보안은 권한 규칙이 대체. 스크립트 파일은 `ccgs/hooks/`에 보존되어 있어 추후 OpenCode 플러그인으로 재작성 가능 |
| `statusLine` | 세션 상태 표시줄 | OpenCode에 동등 설정 없음(무시됨) |
| 경로별 룰 자동주입 (`.claude/rules/`) | 편집 중인 파일 경성에 따라 코딩 규칙 자동 주입 | OpenCode는 경로 스코프 규칙 미지원. 파일은 `ccgs/rules/`에 보존(필요 시 수동 참조) |
| `$CLAUDE_PROJECT_DIR` 등 환경변수 | 훅/스킬이 프로젝트 루트를 찾는 변수 | OpenCode엔 없음 → 포트가 절대경로/상대경로로 치환. 관련 문서(`ccgs/docs/config-resolution.md`)에 포트 노트 자동 추가 |

**알려진 제약**

- 전역 설치는 **모든 폴더**에 스튜디오가 로드됩니다(훅 제외). 프로젝트별
  적용은 `/adopt`로 `project.yaml`을 만든 폴더에서 완전히 동작합니다.
- 서브에이전트의 모델은 원본의 `opus/sonnet` 지정을 버리고 **세션 모델을
  상속**합니다(원하는 경우 에이전트 파일에 `model: provider/model` 추가).
- 에이전트 대부분이 쓰기 권한을 기본 deny로 제한했으므로(읽기 전용 에이전트),
  원본 `tools` 목록에 없는 도구는 차단됩니다. 필요한 에이전트는 해당
  `agents/<id>.md`의 `permissions`를 수정하세요.
- OpenCode의 `AGENTS.md`는 Claude Code의 `@path` import 문법을 지원하지
  않습니다. 엔진 레퍼런스 고정(`@docs/engine-reference/<engine>/VERSION.md`)
  등 import 기반 동작은 해당 내용을 직접 기재하는 방식으로 대체하세요.

### 검증 결과 (최종 실측)

```
skills=74  agents=49  commands=74  ccgs_files=198  permission_rules=84
bash -n: 0 / 51                 # 이식된 bash 스크립트 전부 구문 검사 통과
frontmatter problems: 0         # 49개 에이전트 전부 OpenCode V2 스키마 파싱 통과
Claude-isms 잔여(코드 기준): 0    # CLAUDE.md / AskUserQuestion / claude CLI / ${CLAUDE_*} = 0
기능 테스트: 통과                 # 프로젝트 루트 해석(하위폴더 포함), project.yaml 읽기, resolve_config
```

OpenCode 세션에서 스킬 74개가 정상 등록되고 전역 `AGENTS.md`와
`opencode.jsonc` 변경사항이 설정 로드에 반영되는 것을 확인했습니다.

### 포트 수정 이력 (v1.2.1–v1.2.2 — 사용 중 발견·수정)

포팅 후 실제 사용 중 보고된 오류들과, 이어서 진행한 전면 재감사에서 찾은
결함들을 근본 원인까지 추적해 모두 고쳤습니다. 아래 항목들은 **원본 버그가
아니라, 포팅 과정에서 생긴 결함**입니다.

**1) `${...}` 중괄호 형태 환경변수 누락 → bash 구문 오류**

- 증상: `CLAUDE_PROJECT_DIR` 관련 오류, `yaml-helper.sh: line 766: syntax
  error near unexpected token '('`
- 원인: 포트의 치환이 `$CLAUDE_PROJECT_DIR`(달러 직결)만 처리하고
  `${CLAUDE_PROJECT_DIR}`·`${CLAUDE_PROJECT_DIR%/}`·`${CLAUDE_PROJECT_DIR:-}`
  등 중괄호 형태 61건을 통과시켰다. 게다가 사용한 정규식 `[^}/\s]*`가 중괄호
  없는 변수 뒤의 `"`·`;`까지 삼켜 `_YH_ROOT="."; return 0`가
  `_YH_ROOT=". return 0`으로 망가지는 2차 손상이 발생 — 따옴표 불균형이
  bash 파싱을 깨뜀렸다
- 수정: 정규식을 "중괄호/비중괄호 분리 + trailing punctuation 보존"으로 재작성,
  24개 파일의 변수 참조를 전부 안전 치환. `bash -n` 51/51 통과로 검증

**2) 프로젝트 루트 앵커가 설정 폴더를 가리킴**

- 증상: `project.yaml`이 없는 프로젝트에서 `project-state.sh` 등의 root 출력이
  `C:/Users/<user>/.config/opencode`(OpenCode 설정 폴더)로 잘못 표시
- 원인: 원본 스크립트 31개가 `cd "$HERE/../.."`로 "스크립트 위치 2단계 위 =
  프로젝트 루트"를 가정한다. 원본 레이아웃(프로젝트 안에 `.claude/` 존재)에선
  맞지만, 전역 설치에선 그 위치가 설정 폴더가 된다
- 수정: 포트가 앵커를 `ccgs_project_root()` 리졸버로 교체하고 스크립트마다
  주입 — 프로젝트 루트 = 실행 디렉터리, 없으면 `project.yaml`이 있는 가장 가까운
  상위 디렉터리(서브폴더 실행도 upstream과 동일하게 동작). 프레임워크 트리
  조회용 `CCGS_ROOT`는 의도적으로 유지
- 검증: 프로젝트 루트·하위 폴더(`design/gdd`) 양쪽에서 루트 해석과
  `project.yaml` 읽기 정상 동작 확인

**3) yaml-helper 셀프 루트 폴백 동일 문제**

- 수정: 두 분기 모두 위의 상위 탐색으로 교체

**4) 기타 정리**

- `${CLAUDE_SKILL_DIR}/../../` → ccgs 루트 절대경로, 그 외 형태는 스킬 자신의
  설치 디렉터리로 치환
- `subagent_type: X` → OpenCode식 서브에이전트 표현으로 치환(대괄호
  플레이스홀더 포함), `AskUserQuestion` → `question` 도구 표현(잔여 0)
- `ccgs/docs/config-resolution.md`에 OpenCode 포트 노트 자동 주입(멱등)

**5) `CLAUDE.md` 참조 — OpenCode가 읽지 않는 파일을 편집하라던 문제**

- 증상: 없음(사용자 "오류 있으면 안 된다" 요청으로 전면 재감사에서 발견).
  `setup-engine` 등 27개 파일이 `CLAUDE.md`를 참조/편집 대상으로 지목
- 원인: Claude Code는 프로젝트 지시를 `CLAUDE.md`에서 읽지만, **OpenCode는
  `AGENTS.md`**에서 읽는다. 포팅이 이 매핑을 빠뜨리면 스킬이 "CLAUDE.md의
  Technology Stack을 업데이트하라"고 해도 OpenCode는 그 파일을 읽지 않음 —
  조용히 무시되는 설정
- 수정: 본문·**frontmatter description**·참고 파일명까지 `CLAUDE.md` →
  `AGENTS.md`로 치환(`4-claude-md-stack.md` → `4-agents-md-stack.md` 이름
  변경 포함). 프레임워크 자신의 지시 파일은 `ccgs/studio-reference.md` +
  `ccgs/AGENTS.md`로 보존
- 검증: 설치 트리에서 `CLAUDE.md` 잔여 0건

**의도적으로 남겨둔 것**: `agent-check.sh`·`compat-inventory.sh` 등 린터/진단
스크립트가 Claude 토큰을 **탐지 대상**으로 쓰는 패턴, 훅 스크립트 내 주석,
업스트림 `CLAUDE.md` 참고용 원본(`ccgs/studio-reference.md`) — 이들은 실행
경로에 영향 없음.

### 업데이트 / 제거

```bash
# 원본 최신화 → 재포트
git pull
python port/port.py

# 제거: ~/.config/opencode/ 에서 skills/<id> agents/<id>.md commands/<id>.md
# ccgs/ 디렉터리와 opencode.jsonc의 permissions 블록을 삭제하면 원상복구
```

### 크레딧

- 원본: [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) — MIT License
- 이 포팅은 원본의 **파생 저작물**이며 동일하게 MIT로 공개합니다.

---

---

<p align="center">
  <sub>↑ 포팅 설명 끝 · 아래부터는 원본 README(업스트림 그대로)입니다 ↓</sub>
</p>

---

# 📖 원본 README — Claude Code Game Studios

<p align="center">
  <sub>Donchitos/Claude-Code-Game-Studios v1.2.0 원문 · <strong>Claude Code 전용 문서</strong>이므로
  일부 표현(슬래시 커맨드 실행 환경, 훅, statusline 등)은 이 포팅 버전에선 적용되지 않습니다</sub>
</p>

<p align="center">
  <h1 align="center">Claude Code Game Studios</h1>
  <p align="center">
    Turn a single Claude Code session into a full game development studio.
    <br />
    49 agents. 74 skills. One coordinated AI team.
  </p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href=".claude/agents"><img src="https://img.shields.io/badge/agents-49-blueviolet" alt="49 Agents"></a>
  <a href=".claude/skills"><img src="https://img.shields.io/badge/skills-74-green" alt="74 Skills"></a>
  <a href=".claude/hooks"><img src="https://img.shields.io/badge/hooks-15-orange" alt="15 Hooks"></a>
  <a href=".claude/rules"><img src="https://img.shields.io/badge/rules-14-red" alt="14 Rules"></a>
  <a href="https://code.claude.com/docs"><img src="https://img.shields.io/badge/built%20for-Claude%20Code-f5f5f5?logo=anthropic" alt="Built for Claude Code"></a>
  <a href="https://www.buymeacoffee.com/donchitos3"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support%20this%20project-FFDD00?logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee"></a>
  <a href="https://github.com/sponsors/Donchitos"><img src="https://img.shields.io/badge/GitHub%20Sponsors-Support%20this%20project-ea4aaa?logo=githubsponsors&logoColor=white" alt="GitHub Sponsors"></a>
</p>

---

## Why This Exists

Building a game solo with AI is powerful — but a single chat session has no structure. No one stops you from hardcoding magic numbers, skipping design docs, or writing spaghetti code. There's no QA pass, no design review, no one asking "does this actually fit the game's vision?"

**Claude Code Game Studios** solves this by giving your AI session the structure of a real studio. Instead of one general-purpose assistant, you get 49 specialized agents organized into a studio hierarchy — directors who guard the vision, department leads who own their domains, and specialists who do the hands-on work. Each agent has defined responsibilities, escalation paths, and quality gates.

The result: you still make every decision, but now you have a team that asks the right questions, catches mistakes early, and keeps your project organized from first brainstorm to launch.

---

## Table of Contents

- [What's Included](#whats-included)
- [Studio Hierarchy](#studio-hierarchy)
- [Slash Commands](#slash-commands)
- [Does it produce games, or documents?](#does-it-produce-games-or-documents)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Upgrading](#upgrading)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Design Philosophy](#design-philosophy)
- [Customization](#customization)
- [Platform Support](#platform-support)
- [Community](#community)
- [Supporting This Project](#supporting-this-project)
- [License](#license)

---

## What's Included

| Category | Count | Description |
|----------|-------|-------------|
| **Agents** | 49 | Specialized subagents across design, programming, art, audio, narrative, QA, and production |
| **Skills** | 74 | Slash commands for every workflow phase (`/start`, `/design-system`, `/create-epics`, `/create-stories`, `/dev-story`, `/story-done`, etc.) |
| **Hooks** | 15 | Automated validation on commits, pushes, asset changes, design-doc reads, writes and registries, session lifecycle, agent audit trail, and gap detection |
| **Rules** | 14 | Path-scoped coding standards enforced when editing gameplay, engine, AI, UI, network code, scene and asset files, and more |
| **Templates** | 62 | Document templates for GDDs, UX specs, ADRs, sprint plans, HUD design, accessibility, and more |

## Studio Hierarchy

Agents are organized into three tiers, matching how real studios operate:

```
Tier 1 — Directors
  creative-director    technical-director    producer

Tier 2 — Department Leads
  game-designer        lead-programmer       art-director
  audio-director       narrative-director    qa-lead
  release-manager      localization-lead

Tier 3 — Specialists
  gameplay-programmer  engine-programmer     ai-programmer
  network-programmer   tools-programmer      ui-programmer
  systems-designer     level-designer        economy-designer
  technical-artist     sound-designer        writer
  world-builder        ux-designer           prototyper
  performance-analyst  devops-engineer       analytics-engineer
  security-engineer    qa-tester             accessibility-specialist
  live-ops-designer    community-manager
```

Each agent declares a model in its frontmatter: the three directors ask for
Opus, `lead-programmer` and fifteen specialists name Sonnet, and the remaining thirty
**inherit your session's model**. Treat the tiers as seniority of role, not as
a billing plan — most of the studio runs on whatever model you are already using.

### Engine Specialists

The template includes agent sets for all three major engines. Use the set that matches your project:

| Engine | Lead Agent | Sub-Specialists |
|--------|-----------|-----------------|
| **Godot 4** | `godot-specialist` | GDScript, Shaders, GDExtension |
| **Unity** | `unity-specialist` | DOTS/ECS, Shaders/VFX, Addressables, UI Toolkit |
| **Unreal Engine 5** | `unreal-specialist` | GAS, Blueprints, Replication, UMG/CommonUI |

## Slash Commands

Type `/` in Claude Code to access all 74 skills:

**Onboarding & Navigation**
`/start` `/help` `/project-stage-detect` `/setup-engine` `/adopt` `/settings`

**Game Design**
`/brainstorm` `/map-systems` `/design-system` `/quick-design` `/review-all-gdds` `/propagate-design-change`

**Art & Assets**
`/art-bible` `/asset-spec` `/asset-audit`

**UX & Interface Design**
`/ux-design` `/ux-review`

**Architecture**
`/create-architecture` `/architecture-decision` `/architecture-review` `/create-control-manifest`

**Stories & Sprints**
`/create-epics` `/create-stories` `/dev-story` `/sprint-plan` `/sprint-status` `/story-readiness` `/story-done` `/estimate`

**Reviews & Analysis**
`/design-review` `/code-review` `/balance-check` `/content-audit` `/scope-check` `/perf-profile` `/tech-debt` `/gate-check` `/consistency-check` `/security-audit`

**QA & Testing**
`/qa-plan` `/smoke-check` `/soak-test` `/regression-suite` `/test-setup` `/test-helpers` `/test-evidence-review` `/test-flakiness` `/skill-test` `/skill-improve`

**Production**
`/milestone-review` `/retrospective` `/bug-report` `/bug-triage` `/reverse-document` `/playtest-report`

**Release**
`/release-checklist` `/launch-checklist` `/changelog` `/patch-notes` `/hotfix` `/day-one-patch`

**Creative & Content**
`/prototype` `/vertical-slice` `/onboard` `/localize`

**Team Orchestration** (coordinate multiple agents on a single feature)
`/team-combat` `/team-narrative` `/team-ui` `/team-release` `/team-polish` `/team-audio` `/team-level` `/team-live-ops` `/team-qa`

## Does it produce games, or documents?

A fair question, and the answer is a measurement rather than a sample project.
Four games were built from one brief at different `modes.rigor` levels and the
documents each wrote **before its first line of game code** were counted:

| `modes.rigor` | Docs before first line of game code | Time |
|---|---:|---:|
| `minimal` | **1** (the one-page brief) | 0 min |
| `standard` | 30 | 58 min |

All of them produced a running, tested game. Two blind reviewers and a human
playtest then ranked the `standard` build **last** — the extra 29 documents
bought traceability, not a better game.

### It runs the game and looks at it

The measurement above is about cost. The other half is whether the thing works,
and for a game that means someone has to *look* at it — a passing test says
nothing about a menu drawn off-screen. So a story that changes anything the
player sees is not closed until the game has been launched, observed, and a
screenshot retained in `production/qa/evidence/`. A parse check is not a run.
This holds at every rigor level, including `minimal`, where automated tests are
waived but the look is not.

The games themselves are deliberately **not** shipped here: this is a template
you clone to start your own project, and somebody else's game in your repo is
clutter, not evidence.

## Getting Started

### Prerequisites

- [Git](https://git-scm.com/)
- [Claude Code](https://code.claude.com/docs/en/setup) — the native installer is recommended (`npm install -g @anthropic-ai/claude-code` also works, on Node.js 22+)
- [Python 3](https://www.python.org/) — reads `project.yaml` for every skill and hook; without it every setting silently falls back to its default
- Bash — runs every hook; built into macOS and Linux, and on Windows it comes with [Git for Windows](https://git-scm.com/downloads/win)
- **Recommended**: [jq](https://jqlang.github.io/jq/) (for hook validation)

Hooks fail gracefully if optional tools are missing — you just lose validation — with one deliberate exception: a commit that stages data JSON is blocked when there is no Python to validate it.

### Setup

1. **Clone or use as template**:
   ```bash
   git clone https://github.com/Donchitos/Claude-Code-Game-Studios.git my-game
   cd my-game
   ```

2. **Open Claude Code in the project's root folder** (the one holding
   `CLAUDE.md` and `project.yaml`) and start a session:
   ```bash
   claude
   ```
   Starting it in a subfolder such as `src/` skips the project's hooks, deny
   rules and ask-first permission mode.

3. **Run `/start`** — the system asks where you are (no idea, vague concept,
   clear design, existing work) and guides you to the right workflow. No assumptions.

   Or jump directly to a specific skill if you already know what you need:
   - `/brainstorm` — explore game ideas from scratch
   - `/setup-engine godot 4.7` — configure your engine if you already know
   - `/project-stage-detect` — analyze an existing project

## Configuration

`project.yaml` at the repo root is the single source of truth for how the
studio behaves on your project — engine, naming conventions, and a `modes`
block that controls how much process every skill enforces. `/start` writes it
for you; you rarely need to hand-edit it.

The one question that matters most is **`modes.rigor`** — `minimal`, `standard`,
or `full`. It's a single front door over six separate knobs (`workflow` —
which GDD sections are required, `docs.density`, `qa.level`,
`story_granularity`, `review_mode` — how many director agents review your work,
and `team.size`), so `/start` asks it once instead of six times:

- **`minimal`** (default) — jam-game speed. No GDDs required, terse docs, minimal QA evidence, solo review. `/start` → `/setup-engine` → `/brainstorm` (a one-page brief) → `/create-stories` → `/dev-story` ↔ `/story-done`.
- **`standard`** — 5 required GDD sections, balanced doc depth, standard QA evidence, lean review.
- **`full`** — all 8 GDD sections, thorough docs, full QA evidence on every story type, full director review.

`minimal` is the default because the heavier tier costs more to reach working
code without producing a better result, and gives nothing back when someone new
picks the project up. Raise it in one `/settings` call when your project grows
— `/help` and `/gate-check` will suggest it when they see the signs.

Two escape hatches keep one setting from being a blunt instrument.
**`system_overrides`** holds a single system to a higher standard than the rest
of the project — your combat system gets the full treatment while everything
else stays light. **`testing.strict`** sets, per test type (logic, integration,
visual, UI, config), whether missing evidence blocks a story or merely warns.

Any of the six underlying knobs can still be set individually if you want a mix
(e.g. `workflow: full` with `docs.density: terse` — comprehensive but compact).
Two of them — `review_mode` (`full` / `lean` / `solo`) and `team.size` — are
also **personal**: rigor sets the team-wide default, but you can override them
per-developer in a gitignored `project.local.yaml` without touching the shared
config. `modes.automation` (how often the AI pauses to ask before it acts) sits
outside rigor and is likewise personally overridable.

View or change any setting with the `/settings` skill:

```
/settings                              # view effective config
/settings modes.review_mode            # view one setting
/settings modes.rigor=full             # write to project.yaml (team-wide)
/settings --local modes.review_mode=solo   # write to project.local.yaml (just you)
```

Full schema and per-setting behavior: `.claude/docs/effects-map.md`.

## Upgrading

Already using an older version of this template? See [UPGRADING.md](UPGRADING.md)
for step-by-step migration instructions, a breakdown of what changed between
versions, and which files are safe to overwrite vs. which need a manual merge.

## Project Structure

```
CLAUDE.md                           # Master configuration
.claude/
  settings.json                     # Hooks, permissions, safety rules
  agents/                           # 49 agent definitions (markdown + YAML frontmatter)
  skills/                           # 74 slash commands (subdirectory per skill)
  hooks/                            # 18 scripts (bash) — 15 event hooks, two helpers they
                                    #   source (yaml-helper.sh, update-check.sh), and one
                                    #   opt-in diagnostic you wire yourself
  rules/                            # 14 path-scoped coding standards
  statusline.sh                     # Status line script (context%, model, stage, epic breadcrumb)
  docs/
    workflow-catalog.yaml           # 7-phase pipeline definition (read by /help)
    templates/                      # 62 document templates (+ per-section guidance)
src/                                # Game source code (Godot). The code root is
                                    #   ENGINE-SPECIFIC: Unity compiles only
                                    #   Assets/, Unreal builds from Source/<Module>/
assets/                             # Art, audio, VFX, shaders, data files
design/                             # GDDs, narrative docs, level designs
docs/                               # Technical documentation and ADRs
tests/                              # Test suites (unit, integration, performance, playtest)
tools/                              # Build and pipeline tools
prototypes/                         # Throwaway prototypes (isolated from src/)
production/                         # Sprint plans, milestones, release tracking
studio-tests/                       # QA for the skills and agents themselves — see below
```

### Testing your customizations

CCGS is a template you are meant to edit. `studio-tests/` is how
you check that an edited or newly written skill still holds up — a catalog of all
74 skills and 49 agents, per-category quality rubrics, behavioral specs, and
templates for writing specs of your own.

```
/skill-test static [name]     # structural linter — 7 compliance checks
/skill-test category [name]   # category-specific quality rubric
/skill-test spec [name]       # behavioral spec assertions
/skill-test audit             # coverage report across skills and agents
/skill-improve [name]         # test-fix-retest loop; keeps or reverts on score change
```

It tests the *framework*, never your game — game tests live in `tests/`.

## How It Works

### Agent Coordination

Agents follow a structured delegation model:

1. **Vertical delegation** — directors delegate to leads, leads delegate to specialists
2. **Horizontal consultation** — same-tier agents can consult each other but can't make binding cross-domain decisions
3. **Conflict resolution** — disagreements escalate up to the shared parent (`creative-director` for design, `technical-director` for technical)
4. **Change propagation** — cross-department changes are coordinated by `producer`
5. **Domain boundaries** — agents don't modify files outside their domain without explicit delegation

### Collaborative, Not Autonomous

This is **not** an auto-pilot system. Every agent follows a strict collaboration protocol:

1. **Ask** — agents ask questions before proposing solutions
2. **Present options** — agents show 2-4 options with pros/cons
3. **You decide** — the user always makes the call
4. **Draft** — agents show work before finalizing
5. **Approve** — nothing gets written without your sign-off

You stay in control. The agents provide structure and expertise, not autonomy.

That is how a terminal session started at the project root behaves out of the
box. The `guided` and `autonomous` automation settings, and Claude Code's own
auto mode, trade some of these prompts for speed; see
[setup-requirements.md](.claude/docs/setup-requirements.md) for the routes into
auto mode.

### Automated Safety

**Hooks** run automatically on every session:

| Hook | Trigger | What It Does |
|------|---------|--------------|
| `validate-commit.sh` | PreToolUse (Bash, PowerShell) | Checks for hardcoded values, TODO format, JSON validity, design doc sections — exits early if the command is not `git commit` |
| `validate-push.sh` | PreToolUse (Bash, PowerShell) | Warns on pushes to protected branches, and on `git tag`, `git merge`, `gh release`, `butler push` and `steamcmd +run_app_build` — exits early for any other command |
| `validate-read.sh` | PreToolUse (Read) | Refuses a whole-file read of a design doc over 40 KB and answers with its headings, so the retry reads one section (`features.read_guard`) |
| `validate-write.sh` | PreToolUse (Write/Edit) | Warns, never blocks, when a write would break a rule the skills state: a file they never overwrite, the config guard, the prototype boundary, a localization freeze |
| `validate-registry.sh` | PreToolUse (Write/Edit) | Warns when a write to the entity or TR-ID registry would delete or renumber an entry, or set a status its header does not list |
| `validate-assets.sh` | PostToolUse (Write/Edit) | Checks data-file JSON under `assets/`, `Assets/` or `Content/`, and asset naming in Godot's `assets/` only — exits early if the file is under none of them |
| `session-start.sh` | Session open | Shows current branch and recent commits for orientation |
| `detect-gaps.sh` | Session open | Detects fresh projects (suggests `/start`) and missing design docs when code or prototypes exist |
| `pre-compact.sh` | Before compaction | Logs the compaction (its output does not reach Claude — `session-start.sh` restores context afterwards) |
| `notify.sh` | Permission prompt, or idle about a minute | Shows Windows toast notification via PowerShell |
| `session-stop.sh` | Every response end, in the background | Archives `active.md` to session log and records git activity |
| `log-agent.sh` | Agent spawned | Audit trail start — logs subagent invocation |
| `log-agent-stop.sh` | Agent stops | Audit trail stop — completes subagent record |
| `validate-agent-artifact.sh` | Agent stops | Warns when a subagent stops without writing the file its brief named |
| `validate-skill-change.sh` | PostToolUse (Write/Edit) | Advises running `/skill-test` after any `.claude/skills/` change |

> **Note**: `validate-commit.sh`, `validate-push.sh`, `validate-read.sh`, `validate-write.sh`, `validate-registry.sh`, `validate-assets.sh` and `validate-skill-change.sh` fire on every Bash, PowerShell, Read, Write or Edit tool call and exit immediately (exit 0) when the command or file path is not relevant. This is normal hook behavior — not a performance concern.

**Permission rules** in `settings.json` auto-allow test runs and block dangerous operations (force push, `rm -rf`, reading `.env` files) in both the Bash and PowerShell tools. Read-only commands such as `git status`, `git log` and `ls` need no rule: Claude Code runs them without asking. The `git` rules match anywhere after `git`, so a git command whose text only mentions `push` followed later by ` +` or ` -f`, `clean` followed by ` -f`, or `reset` followed by `--hard` — a commit message such as `git commit -m "push + pull"` included — is denied too: reword the message.

### Path-Scoped Rules

Coding standards are automatically enforced based on file location. The paths
below are Godot's. Each rule also matches the Unity and Unreal layouts: the code
rules match C# under `Assets/**/Gameplay/` and C++ under `Source/**/Gameplay/` (and `Core`,
`AI`, `Networking`, `UI`), data matches JSON under `Assets/**/Data/` and
`Content/**/Data/`, shaders match by file type, and tests match
C# under `Assets/Tests/` and C++ under `Source/**/Tests/`.

| Path | Enforces |
|------|----------|
| `src/gameplay/**` | Data-driven values, delta time usage, no UI references |
| `src/core/**` | Zero allocations in hot paths, thread safety, API stability |
| `src/ai/**` | Performance budgets, debuggability, data-driven parameters |
| `src/networking/**` | Server-authoritative, versioned messages, security |
| `src/ui/**` | No game state ownership, localization-ready, accessibility |
| `design/gdd/**` | Required sections per `modes.workflow`, formula format, edge cases |
| `design/narrative/**` | Lore consistency, character voice, canon levels |
| `assets/data/**/*.json` | JSON validity, naming conventions, schema rules |
| `assets/shaders/**` | Naming conventions, performance targets, cross-platform rules |
| `**/*.tscn`, `**/*.tres` | Scene and resource files changed in the editor where possible; safe hand-edit rules |
| `tests/**` | Test naming, coverage requirements, fixture patterns |
| `prototypes/**` | Relaxed standards, README required, hypothesis documented |

## Design Philosophy

This template is grounded in professional game development practices:

- **MDA Framework** — Mechanics, Dynamics, Aesthetics analysis for game design
- **Self-Determination Theory** — Autonomy, Competence, Relatedness for player motivation
- **Flow State Design** — Challenge-skill balance for player engagement
- **Bartle Player Types** — Audience targeting and validation
- **Verification-Driven Development** — Tests first, then implementation

## Customization

This is a **template**, not a locked framework. Everything is meant to be customized:

- **Add/remove agents** — delete agent files you don't need, add new ones for your domains
- **Edit agent prompts** — tune agent behavior, add project-specific knowledge
- **Modify skills** — adjust workflows to match your team's process
- **Add rules** — create new path-scoped rules for your project's directory structure
- **Tune hooks** — adjust validation strictness, add new checks
- **Pick your engine** — use the Godot, Unity, or Unreal agent set (or none)
- **Tune process weight** — `modes.rigor` and its underlying knobs in `project.yaml` (see [Configuration](#configuration)). Override per-run with `--review solo` on any skill.

## Platform Support

Primary development on **Windows 10** with Git Bash. The hooks and scripts are also tested on **macOS** — its stock bash 3.2 and BSD tools, with and without `jq` — and on **Linux**. All hooks use POSIX-compatible patterns (`grep -E`, not `grep -P`) and include fallbacks for missing tools. The `notify.sh` hook uses PowerShell for Windows toast notifications and is a no-op elsewhere — desktop notifications on macOS/Linux are not yet wired. Please file issues for any platform-specific breakage.

## Community

- **Discussions** — [GitHub Discussions](https://github.com/Donchitos/Claude-Code-Game-Studios/discussions) for questions, ideas, and showcasing what you've built
- **Issues** — [Bug reports and feature requests](https://github.com/Donchitos/Claude-Code-Game-Studios/issues)

---

## Supporting This Project

Claude Code Game Studios is free and open source. If it saves you time or helps you ship your game, consider supporting continued development:

<p>
  <a href="https://www.buymeacoffee.com/donchitos3"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/Donchitos"><img src="https://img.shields.io/badge/GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=githubsponsors&logoColor=white" alt="GitHub Sponsors"></a>
</p>

- **[Buy Me a Coffee](https://www.buymeacoffee.com/donchitos3)** — one-time support
- **[GitHub Sponsors](https://github.com/sponsors/Donchitos)** — recurring support through GitHub

Sponsorships help fund time spent maintaining skills, adding new agents, keeping up with Claude Code and engine API changes, and responding to community issues.

---

*Built for Claude Code. Maintained and extended — contributions welcome via [GitHub Discussions](https://github.com/Donchitos/Claude-Code-Game-Studios/discussions).*

## License

MIT License. See [LICENSE](LICENSE) for details.
