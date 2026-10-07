<p align="center">

> **증거 범위:** Hermes는 당시 공개 main `c22ce26bae518e7973f078cac972ea88707b8e79`에서 네이티브 설치했고 설치 후 바이트를 비교했습니다. 로컬 clone의 checkout은 원격 tap/install 명령을 고정하지 않습니다. 실제 사용자 프로필 다섯 곳의 45개 설치와 소비자 업데이트는 운영자 보고이며, 신규 작업 응답은 CLI/Sync 두 패키지만 검증했습니다. `v0.1.0` 거부는 `skills-guard-v6`의 가짜 난스 문자열 두 곳에 대한 `credential_exposure` 오탐입니다. 실제 비밀은 없으며 보안 검사는 우회하지 않았습니다.
  <img src="assets/brand/hero.svg" alt="Obsidian Skills: Obsidian 볼트를 위한 독립된 Agent Skill 스무 개, 네이티브 아홉 개와 지식 열한 개" width="880">
</p>

<p align="center">
  <a href="README.md">English</a> · <b>한국어</b>
</p>

# Obsidian Skills

독립된 Agent Skill 스무 개로 이루어진 `secondbrain-skills` 모음입니다. 네이티브 패키지 아홉 개는 Obsidian 자체를 다룹니다: Markdown, Bases, Canvas, Mermaid, 시각 형식 선택, 공식 CLI, Web Clipper, 볼트 진단, 헤드리스 Sync. 지식 패키지 열한 개는 노트를 다룹니다: `capture`, `inbox`, `ingest`, `query`, `verify`, `audit`, `lint`, `status`, `reindex`, `refresh-context`, `onboard`.

> **현재 배포된 소스.** qmd 파서 수정을 포함한 스무 패키지는 <https://github.com/Xia-Ataraxia/secondbrain-skills>의 0.2.1 릴리스 병합 커밋 `2b1c7e3af129a1536425cdf1d9748abda8768fe6`에 있습니다. 아래의 옛 고정 커밋과 런타임 결과는 과거 증거이며 현재 소스 검증이 아닙니다. 과거 `v0.1.0` 태그는 그대로 두며 현재 모음의 릴리스 식별자는 `0.2.1`입니다. 모든 플러그인 매니페스트가 이 버전을 담고 있어 `0.1.0`을 설치한 호스트도 업그레이드를 인식합니다. 커밋은 자기 해시를 담을 수 없으므로, 권장 소스 고정 커밋은 각 릴리스가 병합된 뒤 별도의 문서 전용 커밋으로 그 병합 커밋으로 옮깁니다.

모든 패키지는 자체 참조 문서와 스크립트를 가진 독립 `SKILL.md`입니다. 루트 스킬도, 디스패처도, 공용 런타임도, 호환 별칭도 없습니다. 에이전트는 그 작업에 필요한 패키지 하나만 불러오고 나머지는 건드리지 않습니다.

> **이력 — 0.1.0 공개 프리릴리스, 그리고 이를 대체하는 수정 고정 커밋. 현재 릴리스는 0.2.1입니다(위 참고).**
> <https://github.com/Xia-Ataraxia/obsidian-skills>에 배포했습니다. 태그 `v0.1.0`(프리릴리스)은 불변 커밋 `0e658b5a09ac4c789392ac634dcff8a195fa3116`에 있으며, 불변이고 **다시 태깅하지 않습니다**. **설치는 수정 커밋 `c22ce26bae518e7973f078cac972ea88707b8e79`**(검증된 설치 소스 리비전)**에서 하고, 태그에서 하지 마십시오.** `v0.1.0` 트리에는 `obsidian-visualize`의 옛 eval 예제가 하드코딩된 플레이스홀더 실행 식별자와 함께 남아 있고 — 실제 비밀이 없는 가짜 문자열 두 곳에서 skills-guard-v6의 credential_exposure 오탐이 발생했으며 실행 의미 분석 결과가 아닙니다 — 실제 Hermes 설치는 그 패키지를 **위험(dangerous)** 으로 표시하고, CLI가 종료 코드 **0**을 반환했는데도 **`Not installed`** 상태로 남겼습니다. 두 커밋 사이에서 달라지는 것은 `obsidian-visualize`뿐이며 나머지 여덟 패키지 트리는 바이트 단위로 동일합니다. 배포 이후 검증한 것: 두 공개 문서가 저장소 호스트에서 렌더되고 원본 SVG 두 개가 대체 텍스트와 함께 로드됐습니다. **이제 네이티브 경로 두 개를 실행했습니다** — Claude Code는 **격리된 소비자 프로젝트 범위 한정**으로 `0e658b5a…`를 분리(detached) 복제한 소스에서 실행했고 그곳에서도 아홉 중 세 패키지만 다뤘습니다. Hermes는 `c22ce26ba…`에서 **일반 운영자 프로필 다섯 곳**에 아홉 패키지를 모두 등록했습니다 — 스킬 가드(`skills-guard-v6`) 기준 **45/45 SAFE**, 강제·우회 플래그 없음. 설치된 각 패키지 트리는 숨김 항목을 제외한 재귀 비교에서 고정 커밋과 바이트 단위로 일치했고, 탭 한정 식별자와 소스 한정 식별자가 모두 해석됐으며, 읽기 전용 신규 세션 다섯 개(`hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills`)가 데스크톱 앱·공식 CLI의 Sync 표면과 헤드리스 `ob` 클라이언트를 정확히 구분했고 앱·볼트·네트워크·계정 작업은 하나도 수행하지 않았습니다. 격리된 앱 프로필에서는 Templater 2.19.3과 Excalidraw 2.27.3이 실제 플러그인 출력을 내놓았습니다. Web Clipper 1.7.1은 폐기용 브라우저 프로필에 설치했고 — 처음의 페이지 타겟 없음 문제는 복구했습니다 — 팝업이 실제 페이지를 노트 미리보기로 추출했습니다. 미검증인 것은 볼트로의 전달뿐입니다: 대상이 *Last used*로 남아 있어 *Add to Obsidian*을 누르지 않았습니다. 아직 미검증: 실행하지 않은 네이티브 경로 세 개(Codex·GJC·Grok), 네이티브 경로 자체가 없는 Cursor·벤더 중립 Agent Skills의 런타임 발견, Hermes에 등록만 되고 호출되지 않은 일곱 패키지의 작업 실행, `hermes skills trust` 이후의 프로젝트 범위 로드, 보호된 볼트·운영 볼트에 대한 쓰기, 전체 소유권 이전, 기존 소유자 은퇴, 실제 계정 Sync. 그 두 경로를 제외하면 경로 확인은 여전히 설치 검증이 아니며, 등록은 호출이 아닙니다. 로컬 소스를 문서화한 런타임(Claude Code, Codex, Grok)은 네이티브 경로를 `c22ce26ba…`로 고정한 복제본으로 지정할 수 있고, 그 외에는 Agent Skills 디렉터리 가져오기(`./install.sh copy`)를 사용합니다.

---

## 왜 필요한가

- **형식마다 소유자는 하나.** 위키링크 질문은 `obsidian-markdown`으로, `.canvas` 그래프는 `obsidian-canvas`로 갑니다. 어떤 패키지도 다른 패키지를 대신해 몰래 답하지 않으므로 답의 출처를 감사할 수 있습니다.
- **능력은 권한이 아니다.** 형식을 안다고 쓰기 권한이 생기지 않습니다. 각 패키지는 정확한 대상 경로, 승인된 효과, 그리고 실제로 변경된 경로에서의 재확인(readback)을 요구합니다.
- **증거 등급을 섞지 않는다.** 파싱은 렌더링이 아니고, 디스크의 파일은 앱이 색인했다는 증거가 아니며, 종료 코드는 쓰기가 되었다는 증거가 아닙니다. 각 패키지는 자신이 도달한 등급을 밝힙니다.
- **무관한 내용은 그대로 남는다.** 부분 편집은 대상이 아닌 노트·프론트매터·ID·첨부를 보존하고, 그 사실을 장담이 아니라 해시로 보고합니다.

<p align="center">
  <img src="assets/demo/workflow.svg" alt="3단계 워크플로: 합성 필드 노트 확인, 독립된 형식 소유자 선택, 구조 검증 후 결과 재확인" width="880">
</p>

<p align="center"><sub>이 저장소를 위해 직접 그린 합성 일러스트입니다 — 스크린샷이 아니며, 실제 렌더링을 주장하지 않습니다.</sub></p>

## 아홉 개 패키지

| 패키지 | 소유 범위 | 첫 사용 예 |
| --- | --- | --- |
| `obsidian-markdown` | Obsidian Flavored Markdown: 위키링크, 임베드, 콜아웃, 프로퍼티, 태그, 블록 참조, 수식, 각주. 비대상 보존과 재확인을 갖춘 정확한 부분 편집. | *"`Notes/Inbox.md`의 프로퍼티와 콜아웃만 고치고 나머지는 건드리지 마."* |
| `obsidian-bases` | `.base` 데이터베이스 뷰: YAML 스키마, 필터, 수식, 요약, table·cards·list·kanban·map 뷰, 그룹·정렬·제한, 그리고 완결된 로컬 함수 레퍼런스. | *"프로젝트 노트를 status로 묶은 Base 뷰를 만들어줘."* |
| `obsidian-canvas` | JSON Canvas 1.0 `.canvas` 문서: 노드·엣지 스키마, 좌표, 색상, 안정적인 ID, 검증. | *"이 노트 다섯 개를 라벨 붙은 엣지가 있는 캔버스 맵으로 만들어줘."* |
| `obsidian-mermaid` | 설치된 앱이 실제로 탑재한 Mermaid 빌드에서 렌더되는 블록: 다이어그램 계열 선택, 버전 게이트 문법, 대체안, 렌더 QA. | *"이 mermaid 블록이 읽기 모드에서 파스 오류가 나 — 고쳐줘."* |
| `obsidian-visualize` | 노트에 맞는 시각 형식(표, 캔버스, Mermaid, Excalidraw) 선택과, 표준 라이브러리만 쓰는 결정론적 `.excalidraw.md` 장면 생성. | *"이 비교에는 어떤 시각화가 맞는지 고르고 그려줘."* |
| `obsidian-cli` | 공식 `obsidian` 바이너리: 읽기, 생성, 검색, 이동, 덧붙이기, 프로퍼티·작업·태그·링크 감사, 플러그인/테마 개발 루프. | *"터미널에서 노트를 만들고 그 경로에서 그대로 다시 읽어줘."* |
| `obsidian-clipper` | Obsidian Web Clipper 캡처: 템플릿, 선택자, 변수, 페이지→노트 매핑. | *"출처와 저자를 남기는 아티클용 Clipper 템플릿을 만들어줘."* |
| `obsidian-doctor` | 민감정보를 제거한 증거로 플러그인·Templater 실패를 진단하는 읽기 전용 분류 스크립트. | *"새 노트에서 Templater가 안 돌아 — 증거를 분류해줘."* |
| `obsidian-sync` | Obsidian Sync용 헤드리스 `ob` 클라이언트(npm `obsidian-headless`): 페어링, 방향 선택, 단발/연속 실행, 사고 수습. | *"서버에 pull-only 헤드리스 동기화를 되돌릴 수 있게 세팅해줘."* |

## 지식 패키지 열한 개

이 열한 패키지는 현재 배포된 소스에 포함됩니다. 아래의 과거 런타임 증거는 원래 리비전에 묶여 있습니다.

| 패키지 | 소유 범위 |
| --- | --- |
| `capture` | 명시적으로 고른 탭, URL, 파일, 대화, 세션 구간을 Inbox 후보로 저장합니다. |
| `inbox` | Inbox 후보를 나열·미리보기·집계하고, 고른 범위를 `ingest`로 넘깁니다. |
| `ingest` | 고른 원본 증거를 Raw에 보존하고 원본에 근거한 Wiki 노트로 정리합니다. 직접 ingest에는 `capture`가 필요 없습니다. |
| `query` | 기존 노트에서 검증된 인용, 상속된 출처, 정확한 Obsidian 딥링크로 답합니다. |
| `verify` | 고른 주장을 검증된 증거와 대조하고 승인에 묶인 기록을 준비합니다. |
| `audit` | 범위를 정해 품질 위험을 표본 점검하고 포괄 범위와 한계를 밝힙니다. |
| `lint` | 정해진 범위의 구조, 인용, 프로퍼티, 링크, 파생 색인 어긋남을 검사합니다. |
| `status` | 지정한 루트에서 읽기 전용 개수, 적체, 스냅숏 경과를 보고합니다. |
| `reindex` | 감사한 컬렉션 하나의 검색 파생물을 격리된 이름의 색인에서 갱신합니다. |
| `refresh-context` | 제안된 파생 컨텍스트 스냅숏을 정확한 원본 해시에 묶고, 승인된 경로만 적용합니다. |
| `onboard` | 검토한 후보로 독립된 개인 볼트나 지식 볼트를 초기화하거나, 추가 설정 변경을 미리 보여줍니다. |

체크아웃에 스무 개 중 어떤 패키지가 들어 있는지는 `./install.sh skills`로 확인합니다.

## 설치

### 1. 배포된 고정 커밋 또는 이미 가진 체크아웃에서 시작

```sh
git clone https://github.com/Xia-Ataraxia/secondbrain-skills
cd secondbrain-skills
git checkout 2b1c7e3af129a1536425cdf1d9748abda8768fe6   # current 0.2.1 release source (twenty packages)
./install.sh skills      # which of the twenty packages are present here
./install.sh routes      # 런타임별 공식 경로, 매니페스트, 스킬 디렉터리
```

위 현재 소스 고정 커밋에는 스무 패키지와 qmd 파서 수정이 포함됩니다. 아래의 옛 `c22ce26bae518e7973f078cac972ea88707b8e79` 고정 커밋은 아홉 패키지 Hermes 설치 증거이며 현재 모음이 아닙니다. 과거 `v0.1.0` 태그는 불변이며 다시 태깅하지 않습니다.

네트워크에 접속하는 단계는 복제뿐입니다. `install.sh`는 네트워크에 접속하지 않고 런타임의 설치·마켓플레이스 명령도 실행하지 않습니다. 이미 가진 로컬 체크아웃도 똑같이 동작합니다 — 배포로 달라진 것은 어떤 소스 형식이 해석되는지이며, 온보딩 방식은 그대로입니다.

### 2. 런타임 스킬 디렉터리로 복사 (지금 동작하는 경로)

```sh
# 기본은 드라이런: 충돌 보고서만 출력하고 아무것도 쓰지 않습니다.
./install.sh copy --runtime cursor --skill all --scope user

# 같은 계획을 실제로 복사.
./install.sh copy --runtime cursor --skill all --scope user --apply

# 사용자 프로필 대신 소비자 프로젝트에 한 패키지만.
./install.sh copy --runtime claude --skill obsidian-markdown \
  --scope project --project-root ~/work/notes --apply
```

`--scope user`는 해당 런타임의 사용자 스킬 디렉터리를, `--scope project`는 `<프로젝트 루트>/<런타임 스킬 디렉터리>`를 대상으로 하며 이 체크아웃 자신을 대상으로 지정하면 거부합니다. 디렉터리 복사는 일반 Agent Skills 가져오기이며, 설치 스크립트는 이를 네이티브 플러그인 설치라고 표기하지 않습니다.

### 3. 런타임별 네이티브 경로

`./install.sh native --runtime <id>`는 해당 런타임의 네이티브 명령을 그 경로를 확인한 근거와 함께 출력할 뿐 실행하지 않습니다. 아래의 `<source>`는 배포된 `Xia-Ataraxia/secondbrain-skills`, 또는 고정 커밋으로 체크아웃한 로컬 복제본의 경로입니다.

| 런타임 | 경로 종류 | 이 저장소의 매니페스트 | 스킬 디렉터리 — 사용자 / 프로젝트 | 네이티브 경로 (출력만, 절대 실행하지 않음) |
| --- | --- | --- | --- | --- |
| `claude` — Claude Code | plugin-marketplace | `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` | `~/.claude/skills` / `.claude/skills` | `claude plugin marketplace add <source>` → `claude plugin install obsidian-skills@obsidian-skills` (`--scope user\|project\|local`, 기본값 user) |
| `codex` — Codex / ChatGPT 데스크톱 앱 | plugin-marketplace | `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json` | `~/.agents/skills` / `.agents/skills` | `codex plugin marketplace add <source>` → `codex plugin add obsidian-skills@obsidian-skills`; 설치 지점은 ChatGPT 데스크톱 앱의 Plugins Directory이며 등록 후 앱을 재시작합니다 |
| `gjc` — GJC (Gajae Code) | plugin-marketplace | `.claude-plugin/marketplace.json` | `~/.gjc/agent/skills` / `.gjc/skills` | `gjc plugin marketplace add Xia-Ataraxia/secondbrain-skills` → `gjc plugin install obsidian-skills@obsidian-skills --scope user`; 도움말이 `<source>`만 문서화하므로 로컬 경로 형식은 주장하지 않습니다 |
| `grok` — Grok Build | plugin-marketplace (문서화된 Claude Code 호환) | `.claude-plugin/marketplace.json` — Grok 전용 매니페스트는 없음 | `~/.grok/skills` / `.grok/skills` | `grok plugin marketplace add <source>` 후 TUI Marketplace 탭에서 설치; 직접 설치는 `grok plugin install Xia-Ataraxia/secondbrain-skills` (git URL·GitHub 단축형·로컬 경로이며 `plugin@marketplace`는 받지 않음) |
| `hermes` — Hermes Agent | registry-tap (스킬 단위) | 없음 | `~/.hermes/skills` / `.hermes/skills` | `hermes skills tap add Xia-Ataraxia/secondbrain-skills` → `hermes skills install Xia-Ataraxia/secondbrain-skills/<name>` → `hermes skills update`; 탭 없이 설치하면 식별자에 경로가 들어갑니다: `…/secondbrain-skills/skills/<name>`; 프로젝트 스킬은 `hermes skills trust` 이후에만 로드됩니다 |
| `cursor` — Cursor | skill-directory | 없음 | `~/.cursor/skills` / `.cursor/skills` | **자가 등록형 네이티브 경로 없음:** Marketplace는 심사·제출 방식이고 팀 마켓플레이스는 Teams/Enterprise 기능이며, Agent Plugin은 이 패키지가 제공하지 않는 루트 `plugin.json`을 요구합니다. 디렉터리 가져오기를 사용하세요. |
| `agent-skills` — 벤더 중립 | skill-directory | 없음 | `~/.agents/skills` / `.agents/skills` | **네이티브 경로 없음:** 이 명세는 패키지 형식만 정의합니다. Codex·Cursor·Grok이 모두 `~/.agents/skills`를 읽으므로 이 범위가 이식성 있는 사용자 수준 가져오기입니다. |

이 표에 적용되는 네 가지 한계:

- **경로 확인은 설치 검증이 아닙니다 — 정확히 둘만 예외입니다.** 각 행은 문서 또는 로컬 CLI 증거를 따로 표시합니다. GJC는 공개 문서가 아닌 설치된 CLI 증거를 사용합니다. 실제로 실행한 네이티브 행은 두 개입니다. *Claude Code*는 격리된 소비자 프로젝트에서: 마켓플레이스 등록과 `claude plugin install obsidian-skills@obsidian-skills --scope project`가 모두 성공을 반환했고, `0e658b5a…`를 분리로 복제한 소스에서 0.1.0을 설치했으며, 그곳에서 새로 로드된 것은 아홉 중 세 패키지입니다. *Hermes*는 `c22ce26ba…`에서: `hermes skills tap add` 뒤에 패키지별 `hermes skills install`로 아홉 패키지를 일반 운영자 프로필 다섯 곳에 모두 등록했습니다 — 스킬 가드(`skills-guard-v6`) 기준 45/45 SAFE, 강제·우회 플래그 없음 — 설치된 각 패키지 트리는 숨김 항목을 제외한 재귀 순회에서 고정 커밋과 바이트 단위로 비교됐고, 탭 한정 식별자 `Xia-Ataraxia/obsidian-skills/<name>`와 소스 한정 식별자 `Xia-Ataraxia/obsidian-skills/skills/<name>`가 모두 해석됐습니다. 나머지 네이티브 경로 세 개 — Codex·GJC·Grok — 는 실행하지 않았습니다. Cursor와 벤더 중립 Agent Skills는 실행할 네이티브 경로 자체가 없으며, 그 경로인 디렉터리 복사는 설치 스위트가 폐기용 루트에서 검증합니다 — 파일 복사는 런타임 발견이 아닙니다.
- **등록은 호출이 아닙니다.** Hermes에서는 `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills`로 읽기 전용 신규 세션 다섯 개를 실행했습니다. 각 세션은 데스크톱 앱·공식 CLI의 Sync 표면과 헤드리스 `ob` 클라이언트를 구분했고, 앱·볼트·네트워크·계정 작업은 하나도 수행하지 않았습니다. 작업으로 실행한 것은 그 두 패키지뿐입니다. 나머지 일곱 개는 깨끗하게 등록됐을 뿐 한 번도 호출되지 않았으므로 Hermes에서의 동작은 미검증입니다. `hermes skills trust` 이후의 프로젝트 범위 로드도 실행하지 않았습니다.
- **배포된 소스 형식은 해석되지만, 배포된 모든 리비전이 어디서나 설치 가능한 것은 아닙니다.** `Xia-Ataraxia/obsidian-skills`는 실재하는 공개 저장소를 가리킵니다. 상태 블록의 수정 고정 커밋 `c22ce26bae518e7973f078cac972ea88707b8e79`을 사용하십시오. **Hermes 설치에 `v0.1.0` 태그를 쓰지 마십시오:** 그 트리에는 `obsidian-visualize`의 옛 eval 예제가 하드코딩된 플레이스홀더 실행 식별자와 함께 남아 있고, 설치는 해당 패키지를 위험한 것으로 표시했으며, CLI가 종료 코드 0을 반환했는데도 레지스트리는 `Not installed`로 보고했습니다 — 종료 상태는 결과가 아니라는 또 하나의 사례입니다. 태그를 다시 달지 않았고 이를 덮기 위한 버전 상향도 하지 않았습니다. 고정은 수정 커밋입니다. 그 커밋으로 고정한 복제본이나 디렉터리 가져오기도 모든 런타임에서 그대로 동작합니다.
- **경로를 출력하는 것은 설치가 아닙니다.** `./install.sh native`는 명령을 출력할 뿐 하나도 실행하지 않고 마켓플레이스나 탭도 등록하지 않으며, 마지막에 그 사실을 명시합니다. 손으로 실행한 두 예외인 Claude Code와 Hermes 경로는 그 출력과 [docs/install-matrix.md](docs/install-matrix.md), [docs/verification-matrix.md](docs/verification-matrix.md)에 모두 적혀 있습니다. 배포된 0.1.0 산출물은 불변이고 다시 태깅하지 않으므로, 고정 이후에 바로잡은 내용은 그 태그가 담고 있는 것을 바꾸지 않습니다.

설치 후 첫 사용: 하려는 일을 평범한 문장으로 요청하고, 에이전트가 패키지를 고르지 못하면 이름을 지정하세요. 예: *"`obsidian-canvas`로 이 노트들을 맵으로 배치해줘."* 격리된 소비자 프로젝트에 설치한 Claude Code에서는 런타임이 패키지를 `obsidian-skills:<name>` 형태로 노출했습니다: `obsidian-skills:obsidian-cli`와 `obsidian-skills:obsidian-sync`의 새 Skill 호출을 기록했고, `obsidian-skills:obsidian-canvas`는 별도의 새 응답에서 답했습니다. Hermes는 대신 각 패키지를 자체 레지스트리 식별자로 다루며 — 번들이 아니라 스킬 단위 하나씩 — `hermes chat --skills <name>[,<name>] --toolsets skills`가 패키지 이름만으로 선택합니다. GJC도 설치된 CLI 증거를 근거로 같은 `obsidian-skills:<name>` 형식을 문서화합니다. 나머지 런타임이 어떤 형태로 노출하는지는 여기서 주장하지 않습니다.

### 요구 사항

| 대상 | 필요한 것 | 여기서 확인한 버전 |
| --- | --- | --- |
| 렌더링·색인이 필요한 모든 작업 | Obsidian 데스크톱 앱 | 1.12.7 (격리된 중립 프로필) |
| `obsidian-cli` | `PATH`에 등록된 공식 `obsidian` CLI | 1.12.7 (installer 1.12.7) |
| `obsidian-doctor`, `obsidian-visualize` 스크립트 | Python 3.9 이상, 표준 라이브러리만 | Python 3.14.7에서 실행; 3.9 런타임 호환성은 미검증 |
| 실제 플러그인 출력 기반 `obsidian-doctor` | 볼트에 설치된 Templater 플러그인 | 격리된 합성 볼트의 2.19.3: 합성 성공 1건과 `is not defined` 실패 1건 관찰 |
| `obsidian-visualize` 장면 렌더링 | 볼트에 설치된 Excalidraw 플러그인 | 같은 격리 볼트의 2.27.3: 요소 다섯 개 장면을 실제 플러그인 뷰에서 렌더 확인 |
| `obsidian-clipper` | Obsidian Web Clipper 브라우저 확장 | 폐기용 브라우저 프로필의 1.7.1: 설정 화면 렌더, 동봉 템플릿 가져오기, 실제 페이지 추출까지 확인; 볼트로의 전달은 미검증 |
| `obsidian-sync` | npm `obsidian-headless`(`ob`)와 Obsidian Sync 계정 | 기존 0.0.14: 도움말 및 미연결 로컬 디렉터리 거부만 확인 |
| 후보 테스트 스위트 실행 | `pip install -r requirements-dev.txt` (PyYAML) | Python 3.14.7 / PyYAML 6.0.3; 로컬 스위트 통과 |

설치 프런트엔드는 POSIX `sh`이며 `copy`는 Python 3.8 이상과 디렉터리 핸들 기반 파일 연산이 필요합니다. 원자적 게시는 macOS/Linux를 지원하며 다른 플랫폼에서는 거부합니다. macOS arm64와 Python 3.14.7에서 시험했고 Linux 및 Python 3.8 런타임 동작은 미검증입니다.

## 안전성

**설치 스크립트**

- 기본은 드라이런이며, 복사하려면 `--apply`가 필요합니다.
- 네트워크에 접속하지 않고, 런타임 자체의 설치·마켓플레이스·클론 명령을 실행하지 않습니다.
- 프로필 설정을 변경하지 않습니다: `settings.json`, `config.toml`, 탭 목록, 레지스트리, 잠금 파일 어느 것도 건드리지 않습니다. 쓰기는 핸들로 고정한 경로 디렉터리, 임시 준비 영역, 선택한 패키지 대상을 포함합니다. 검증 후 원자적으로 게시하며 기존 대상을 대체하지 않습니다. 생성된 캐시는 제외합니다.
- 선택된 모든 패키지를 먼저 점검합니다. 대상 위치에 파일·디렉터리·심링크·끊긴 심링크가 이미 있으면 작업 전체를 거부하고 아무것도 쓰지 않습니다 — 부분 복사는 없습니다.
- 이후 게시에 실패하면 보고된 준비 영역이 복구용으로 남을 수 있으며 `SKILL.md`는 `SKILL.unpublished`로 격리합니다. 격리·정리가 불완전하면 경고합니다. 앞서 게시된 패키지는 유지합니다. 보호 범위는 일반적인 동시 사용이며 같은 계정의 악의적인 준비 영역 변조까지 보장하지 않습니다.
- 스킬 이름은 소문자 경로 세그먼트 하나여야 하며, 대상은 확인된 실제 루트 안에 있고 이 소스 체크아웃 밖에 있어야 합니다.
- 알 수 없는 런타임은 추측하지 않고 거부합니다(`REFUSED`, 종료 코드 1). 사용법 오류는 종료 코드 2입니다.

**스킬**

- 형식 스킬은 쓰기 권한이 아닙니다. 정확한 볼트, 상대 경로 대상, 적용되는 현행 볼트 정책, 승인된 효과를 먼저 확정합니다. 정책 파일 자체는 필수가 아니지만, 권한이 없거나 충돌이 해결되지 않으면 읽기 전용으로 진행합니다.
- 앱·플러그인·CLI·네트워크 증거의 부재를 성공으로 바꾸지 않으며, 무관한 다른 도구로 대체할 근거로 삼지도 않습니다.
- 변경은 정확한 대상 경로에서 다시 읽어 확인하고, 무관한 노트·프론트매터·ID·첨부는 보존한 뒤 해시로 보고합니다.
- 예시는 합성 데이터이며 텔레메트리를 포함하지 않습니다. 로컬 보조 스크립트는 볼트 내용을 업로드하지 않습니다. 명시적으로 승인한 Sync 등 네트워크 작업은 별도의 데이터 전송 경계를 가지며, 그런 작업까지 오프라인이라고 보장하지 않습니다.
- 복구는 승인된 소스와 설정만 되돌립니다. 사용자 노트를 초기화·미러·삭제·덮어쓰기하는 지름길은 쓰지 않습니다.

자세한 내용: [docs/security-and-privacy.md](docs/security-and-privacy.md).

## 실제로 검증된 것

전체 표: [docs/verification-matrix.md](docs/verification-matrix.md). 경로별 상세: [docs/install-matrix.md](docs/install-matrix.md).

### 로컬 릴리스 후보: 스무 개 패키지

아래 검사는 배포된 리비전이 아니라 로컬 후보에서 실행했습니다. 각 항목은 도달한 등급을 밝힙니다.

- **정적 등록.** Claude 플러그인·마켓플레이스 매니페스트가 네이티브 패키지 아홉 개와 지식 패키지 열한 개를 나열합니다. 매니페스트 항목은 선언일 뿐이며, 어떤 런타임이 패키지를 발견하거나 로드했다는 뜻이 아닙니다.
- **임시 구체화.** 폐기용 프로젝트에 `./install.sh copy --runtime claude --skill all --scope project --apply`를 실행하자 정확히 스무 개의 패키지 디렉터리가 생겼고, 복사된 모든 파일이 체크아웃과 바이트 단위로 같았습니다. 패키지 대상 하나에 심링크를 두자 실행 전체가 종료 코드 1로 거부됐고 폐기용 트리는 바뀌지 않았습니다. 복사는 파일 시스템 사실이지 설치가 아닙니다.
- **로컬 동작.** 후보를 정확히 내보낸 사본에서 테스트 스위트와 인벤토리 감사가 통과합니다. 지식 시나리오는 임시 볼트에서 스크립트로 실행했습니다: 온보딩, 직접 ingest와 query 딥링크, capture에서 Inbox를 거쳐 ingest까지, 충돌 거부를 포함한 추가 온보딩.
- **확립되지 않음.** 어떤 런타임도 지식 패키지를 로드한 적이 없으며, 아래 네이티브 증거는 배포된 아홉 패키지에 대한 이전의 별개 기록입니다. 자동 발견, 앱·플러그인 실행, Sync, 배포, 앱에서 딥링크가 열리는 것은 여기서 보여주지 않습니다. 앞으로의 런타임 로드는 자체 증거를 갖는 별도 단계입니다.
- **권리 보류.** `ingest`에는 비공개 출처에서 옮겨 온 보조 스크립트 두 개와 그 테스트가 들어 있습니다. 원 출처 권리는 확인되지 않았고 공개 재배포는 보류 상태이며, [PROVENANCE.md](PROVENANCE.md)에 기록되어 있습니다.

### 네이티브 패키지 아홉 개에 대한 이전 증거

**통과 — 로컬·격리·중립 픽스처** (보고서: [tests/evidence/native-app.json](tests/evidence/native-app.json))

- 격리된 합성 볼트에 대한 공식 CLI 1.12.7: `create` → `search` → `move` → 새 경로에서 재확인까지 수행되고 이전 경로는 사라졌으며, 없는 원본에서의 이동은 아무것도 만들지 않았습니다. 대상 충돌 시험에서는 원본·대상·무관한 노트의 해시가 보존됐습니다.
- 격리된 프로필의 Obsidian 1.12.7 데스크톱 앱: 무관한 프로퍼티와 본문이 바이트 단위로 보존된 Markdown 부분 편집, `Field.md`에서 해석된 `Field.canvas`, 필터·그룹·정렬·제한이 적용된 Bases 뷰(2행, 보관 노트 제외, 원본 노트 불변)와 손상된 `.base`를 파싱 불가로 보고하는 동작, 기존 노드가 보존된 채 세 노드·라벨 엣지 두 개로 확장된 캔버스, SVG로 렌더된 `mermaid` 플로차트, 그리고 알 수 없는 다이어그램 종류를 조용히 넘기지 않고 오류로 보고하는 동작.
- 두 README 모두 로컬 렌더링 확인(markdown-it 및 Chromium): 이미지가 대체 텍스트와 함께 로드되고 1200px에서 가로 오버플로가 없습니다. 이것은 배포 이전 기록이며, 공개 호스트 증거는 아래에 따로 있습니다.

**통과 — 배포·공개 렌더링·네이티브 경로 2건** (보고서: [tests/evidence/publication-canary.json](tests/evidence/publication-canary.json))

- 프리릴리스는 `v0.1.0`이 가리키는 불변 커밋 `0e658b5a09ac4c789392ac634dcff8a195fa3116`으로 공개되어 있습니다: 태그 객체 `04f9dfe25157040dd08a8d14158f8a5d2bbc50ca`, 트리 `10dff62e017df86883d5dd4042f065760e576346`, 내려받은 릴리스 아카이브 SHA-256 `74d97b113a590d83bf082ba8c80a8f93b316da5c11cdfbca14d791c556cbb608`, 도달 가능 객체 스캔 결과 커밋 5·트리 57·블롭 95개. 위에서 권장한 수정 고정 커밋 `c22ce26bae518e7973f078cac972ea88707b8e79`은 같은 저장소의 이후 공개 커밋이며, 태그가 붙어 있지 않고 새로 만들지도 않았습니다.
- 영문과 한글 문서를 저장소 호스트에서 Chromium으로 열었습니다: 둘 다 렌더되었고 `assets/brand/hero.svg`와 `assets/demo/workflow.svg`가 대체 텍스트와 함께 로드됐으며, 저장소 상대 링크는 배포 커밋에 실재하는 경로로 해석됐습니다. 로컬 렌더링이 증명할 수 없던 바로 그 공개 렌더링입니다.
- Claude Code, **격리된 소비자 프로젝트** 범위, `0e658b5a…` 공개 커밋을 분리로 복제한 소스에서 설치: 네이티브 마켓플레이스 등록과 `claude plugin install obsidian-skills@obsidian-skills --scope project`가 0.1.0에 대해 성공을 반환했고, 이후 런타임이 `obsidian-skills:obsidian-cli`와 `obsidian-skills:obsidian-sync`의 새 Skill 호출에 응답했으며 `obsidian-skills:obsidian-canvas`는 별도의 새 응답에서 답했습니다. 그 응답들은 이 저장소가 내건 기준을 그대로 지켰습니다: 충돌 시의 CLI 종료 코드 0을 성공으로 읽지 않았고, 헤드리스 설정 부재를 정상적인 네트워크 Sync로 읽지 않았으며, 끊어진 Canvas 엣지를 노드를 지어내지 않고 거부했고, 파싱과 렌더링을 구분했습니다. 같은 프로젝트의 비대상 센티넬은 이후에도 변하지 않았습니다. 이것은 과거 카나리이며 `0e658b5a…`에 그대로 고정된 기록입니다.

**통과 — Hermes 네이티브 설치와 읽기 전용 세션** (같은 보고서)

- 수정된 공개 고정 커밋 `c22ce26bae518e7973f078cac972ea88707b8e79`에 대해 Hermes 네이티브 registry-tap 경로를 실행했습니다: `hermes skills tap add` 뒤에 패키지마다 `hermes skills install`. 아홉 패키지가 **일반 운영자 프로필 다섯 곳** 각각에 등록됐고 — 스킬 가드(`skills-guard-v6`) 기준 **45/45 SAFE**, 강제·우회 플래그는 어느 곳에서도 쓰지 않았습니다. 이는 실제 로컬 사용자 프로필 배포입니다. 운영자는 네이티브 소비자 업데이트도 보고했지만 전체 소유권 이전을 뜻하지는 않습니다.
- 설치된 각 패키지 트리를 숨김 항목을 제외한 재귀 순회로 소스 고정 커밋과 비교했고 모든 파일이 바이트 단위로 일치했습니다. 레지스트리가 가진 것은 고정된 트리 그 자체이며, 변형되거나 부분적으로 쓰인 사본이 아닙니다.
- 등록 식별자 두 형식이 모두 해석됐습니다: 탭 한정 `Xia-Ataraxia/obsidian-skills/<name>`와 소스 한정 `Xia-Ataraxia/obsidian-skills/skills/<name>`.
- 이어서 `hermes chat --skills obsidian-cli,obsidian-sync --toolsets skills`로 **읽기 전용** 신규 세션 다섯 개를 실행했습니다. 다섯 모두 두 Sync 표면을 하나의 "sync" 답변으로 묶지 않고 구분했습니다 — 한쪽은 데스크톱 앱과 공식 CLI, 다른 한쪽은 헤드리스 `ob` 클라이언트. **그 어느 세션에서도 앱·볼트·네트워크·계정 작업을 수행하지 않았습니다.**
- **작업으로 실행한 것은 `obsidian-cli`와 `obsidian-sync`뿐입니다.** 나머지 일곱 개는 등록만 되고 호출된 적이 없습니다. 등록은 호출이 아니며, Hermes에서의 동작은 미검증입니다. 저장소 내 프로젝트 스킬에 필요한 `hermes skills trust`도 실행하지 않았습니다.
- **발견 — Hermes에 `v0.1.0`을 설치하지 마십시오.** 불변 태그에는 여전히 `obsidian-visualize`의 4단계 핸드셰이크 eval 예제가 하드코딩된 플레이스홀더 실행 식별자와 함께 들어 있습니다. skills-guard-v6가 가짜 난스 문자열 두 곳을 credential_exposure로 오탐했습니다. 실제 비밀은 없었으며 실행 의미 분석 결과가 아닙니다. 설치는 해당 패키지를 **위험한 것으로 표시**했고 **`Not installed`** 상태로 남겼습니다 — 그런데도 CLI는 종료 코드 **0**을 반환했습니다. 종료 상태가 아니라 레지스트리 상태를 읽으십시오. `c22ce26ba…`는 호출자가 새로 생성한 실행 식별자를 대입하도록 요구하며, 두 커밋 사이에서 나머지 여덟 패키지 트리는 바이트 단위로 동일하고, 재태깅이나 버전 상향은 하지 않았습니다.

**통과 — 격리된 앱 프로필의 플러그인** (같은 보고서)

- Obsidian 1.12.7의 격리된 합성 볼트에서 로드한 Templater 2.19.3: 합성 템플릿이 `Synthetic templater result`를 생성했고, 의도적으로 깨뜨린 쪽은 `missingSyntheticVariable is not defined`로 실패했습니다. 성공과 오류 모두 실제 플러그인 출력이며 비대상 노트는 변하지 않았습니다. Templater 2.25.1은 매니페스트가 앱 1.13.0을 요구하므로 버전을 강제하지 않고 호환 버전인 2.19.3을 설치했습니다.
- 같은 볼트의 Excalidraw 2.27.3: 요소 다섯 개 장면이 실제 플러그인 뷰에서 열렸고 — *Study*와 *Evidence* 텍스트 상자가 화살표로 연결 — 뷰와 스크린샷을 직접 확인했습니다. 그 장면 하나에 한해 장면 생성기는 정적 검증이 아니라 렌더 검증 등급에 도달했습니다.

**통과 — Web Clipper 추출, 다만 전달은 미검증** (같은 보고서)

- 공식 Chrome 릴리스 아카이브의 Web Clipper 1.7.1을 별도의 폐기용 브라우저 프로필에 설치했습니다. 첫 부착에서는 페이지 타겟이 없었고, 격리된 점검 페이지를 만들어 복구했습니다. 이후 네이티브 `Extensions.loadUnpacked`가 성공했고, 백그라운드 서비스 워커가 나타났으며, 실제 설정 UI가 렌더됐습니다.
- 동봉된 `clipping-template.json`이 *General clipping* 템플릿으로 가져와졌고, 기본 제공 *Default* 템플릿도 그대로 보존됐습니다.
- `example.org`에서 실제 확장 액션 팝업이 *General clipping*을 선택해 *Example Domain* 제목·출처 URL·본문을 노트 미리보기로 추출했습니다. 선택자 예행연습이 아니라 실제 페이지를 대상으로 한 확장 실행입니다.
- **누르지 않음: *Add to Obsidian*.** 대상이 여전히 *Last used*였기 때문에 클립을 전달하지 않았습니다. 정확한 볼트로의 전달과 생성된 노트 재확인은 미검증입니다. 사용자 브라우저 프로필과 볼트 노트는 전혀 건드리지 않았습니다.

**통과 안의 한계 — 초록색 결과를 믿기 전에 읽으십시오**

- 이 CLI는 오류를 출력하면서도 종료 코드 0을 반환합니다(예: `Error: Destination file already exists!`). 쓰기의 증거는 종료 상태가 아니라 출력과 대상 경로 재확인입니다.
- 잘못된 Bases 식은 명확한 파싱 오류 대신 0행과 오류 성격의 필터 표시를 냈습니다. 빈 행은 검증 성공이 아닙니다.
- 앱 버전 하나, 프로필 하나, 작은 합성 볼트 하나, 단발 실행입니다.
- 공개 렌더링은 호스트 하나·브라우저 하나·커밋 하나입니다. 다른 브라우저·호스트·이후 리비전에 대해서는 아무것도 말하지 않습니다.
- Claude Code 신규 로드는 런타임 하나·격리된 소비자 프로젝트 하나이며 폐기용 분리 복제본에서 설치한 것입니다. 운영 배포도, 다른 런타임도, 소비자 전환도 아닙니다.
- Hermes 결과는 일반 운영자 프로필 다섯 곳에 대한 설치·등록·바이트 검증, 그리고 패키지 두 개에 대한 읽기 전용 세션 다섯 개입니다. 실제 로컬 프로필 배포이지만 볼트·계정 작업은 아니며, 호출된 적 없는 일곱 패키지에 대한 증거도 아닙니다.
- 플러그인 결과는 앱 버전 하나·격리된 합성 볼트 하나·각 플러그인 버전 하나입니다. 운영 볼트·플러그인 설정·계정은 관여하지 않았습니다.

**수행하지 않음 — 지원으로 읽지 마십시오**

- 위에 적은 Claude Code 신규 로드와 Hermes 설치를 제외하면: Codex·GJC·Grok 네이티브 경로는 한 번도 실행하지 않았으며, Cursor와 벤더 중립 Agent Skills는 실행할 네이티브 경로 자체가 없습니다 — 디렉터리 가져오기는 파일 복사일 뿐 런타임 발견이 아닙니다. Hermes의 실제 로컬 사용자 프로필에는 설치했습니다. 전체 운영 준비 완료를 뜻하지는 않습니다. 패키지 단위 실행은 여전히 좁은 범위입니다: Claude Code에서 `obsidian-cli`·`obsidian-sync`·`obsidian-canvas`, Hermes에서 `obsidian-cli`·`obsidian-sync`. 그 외 패키지는 어느 네이티브 런타임에서도 호출된 적이 없습니다.
- Hermes 안에서 `obsidian-markdown`·`obsidian-bases`·`obsidian-mermaid`·`obsidian-visualize`·`obsidian-clipper`·`obsidian-doctor`를 작업으로 실행한 적이 없습니다. 그곳에 등록되어 있다는 것까지만 주장합니다.
- 두 네이티브 결과는 서로 다른 리비전의 것이며 서로에 대한 증거가 아닙니다. Claude Code 카나리는 `0e658b5a…`에만, Hermes 설치는 `c22ce26ba…`에만 존재합니다. 수정 고정 커밋에서 Claude Code 설치나 신규 로드를 실행한 적이 없고, 태그에서의 Hermes 관찰은 거부된 `obsidian-visualize` 건 하나뿐입니다.
- 운영자는 네이티브 소비자 업데이트도 보고했지만, 기존 소유자를 은퇴시키지 않았으며, 변경 이후 활성 소유자·호출자 감사도 없습니다 — [docs/cutover.md](docs/cutover.md)의 5–7단계가 남아 있습니다. 배포된 소비자 변경은 소스 로컬 저작 경로에서 승인(admission)하는 별개 단계이며, 이 저장소의 어떤 것도 그것을 대신하지 않습니다.
- Obsidian Sync 계정 페어링, 원격 볼트 선택, 네트워크 전송, 데몬 실행, 배포 환경 복구는 하지 않았습니다. 실제 계정은 여전히 한 번도 사용하지 않았습니다.
- 운영 플러그인 장애를 재현하지 않았습니다: Templater·Excalidraw 결과는 합성 볼트에서 나온 것이지 실제 프로필의 실제 장애가 아닙니다.
- 볼트로의 Web Clipper 전달: 대상이 *Last used*인 상태에서 의도적으로 *Add to Obsidian*을 누르지 않았으므로, 클립 전달과 그것을 증명할 노트 재확인은 미검증입니다. 추출은 증명됐고 전달은 아직입니다.

**통과 — 로컬 자동 검사**

- 패키지 격리, 형식 계약, 보조 스크립트 동작, 폐기 가능한 설치·복구 사례, 프라이버시, 소스 소유권과 원본 자산 검사가 통과했습니다 — `v0.1.0`이 가리키는 `0e658b5a…` 트리에서 371개 테스트. `c22ce26ba…`는 그리기 보조 스위트에 호출자 난스 사례를 추가했으며, 그 트리의 개수는 여기에 다시 기록하지 않았습니다. 고정된 두 소스의 50개 파일·135개 책임 단위·9개 고유 기능 소유자를 감사했습니다. 재현 명령과 증거 한계는 검증 표에 있습니다.
- 합성 브라우저 선택자는 통과했고 선택자 변경을 감지했습니다. 공개 페이지 선택자는 실패해 그 검사를 중단했습니다. 이것은 DOM 선택자 점검이지 확장 증거가 아닙니다 — 실제 확장 실행은 위에 따로 기록했으며, 클립 전달은 그곳에서도 미검증입니다. Headless 0.0.14는 미연결 임시 디렉터리에 종료 코드 3을 반환했고 계정·네트워크 작업은 수행하지 않았습니다.

## 저장소 구성

```
skills/<name>/           패키지마다 독립 (SKILL.md, references/, scripts/)
install.sh               라우트 테이블 + 충돌 검사 복사 설치 스크립트
assets/                  직접 제작한 브랜드·데모 아트와 asset-ledger.json
docs/                    설치 표, 검증 표, 보안, 전환 절차
tests/                   격리 후보 테스트 스위트 (requirements-dev.txt 참고)
scripts/audit_inventory.py   책임 단위 감사
AGENTS.md                기여자와 에이전트를 위한 저장소 계약
```

## 라이선스와 출처

MIT — 두 저작권 고지가 모두 담긴 [LICENSE](LICENSE)를 참고하십시오.

`obsidian-markdown`, `obsidian-bases`, `obsidian-canvas`, `obsidian-cli`의 일부는 [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)의 커밋 `3ccff5338ea700537839b21900aa5358a0402c98`(MIT, Copyright © 2026 Steph Ango)에서 가져와 수정한 것입니다. 나머지 네이티브 패키지 다섯 개와 지식 패키지 열한 개는 여기서 작성했습니다. 다만 `ingest`의 보조 스크립트 두 개와 그 테스트는 비공개 출처에서 옮겨 왔고 원 출처 권리가 아직 확인되지 않았습니다. [PROVENANCE.md](PROVENANCE.md)를 참고하십시오. 각 패키지의 `CHANGELOG.md`에 정확한 원본 리비전, 가져온 파일, 가한 수정이 모두 기록되어 있습니다.

지식 패키지 열한 개의 작업 구성과 LLM 위키 워크플로는 구요한(Yohan Koo)의 [cmds-llm-wiki](https://github.com/johnfkoo951/cmds-llm-wiki)에서 착안했습니다. 그 저장소 역시 Andrej Karpathy의 LLM Wiki 패턴을 출처로 밝힙니다. 설계상의 영감일 뿐 파일이나 문장은 복사하지 않았으며, 그 저장소는 라이선스를 공개하지 않으므로 여기서 재배포하는 것은 없습니다. 보증이나 제휴 관계를 주장하지 않습니다. [PROVENANCE.md](PROVENANCE.md)를 참고하십시오.

`assets/`의 브랜드·데모 아트는 이 저장소를 위해 직접 제작한 벡터 원본이며, 파일별 제작자·출처·권리는 [assets/asset-ledger.json](assets/asset-ledger.json)에 기록되어 있습니다. 벤더 로고, 아이콘 세트, 애플리케이션 스크린샷은 포함하지 않았습니다. "Obsidian"은 이 스킬들이 대상으로 하는 서드파티 애플리케이션의 이름이며, 제휴나 보증 관계를 주장하지 않습니다.
