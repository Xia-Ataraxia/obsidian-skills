<p align="center">
  <img src="assets/brand/hero.svg" alt="secondbrain-skills: Obsidian 볼트를 위한 독립된 Agent Skill 스물여섯 개, 네이티브 아홉 개와 지식 열일곱 개" width="880">
</p>

<p align="center">
  <a href="README.md">English</a> · <b>한국어</b>
</p>

# secondbrain-skills

에이전트가 Obsidian 볼트를 세컨드 브레인으로 운영하게 해 주는 Agent Skill 스물여섯 개입니다. 자료를 모으고, 원문을 보존하고, 위키로 엮고, 출처를 달아 답합니다.

패키지 하나는 한 가지 일을 맡는 `SKILL.md` 하나입니다. 루트 스킬도, 디스패처도, 공유 런타임도 없습니다. 에이전트는 그 작업에 필요한 패키지만 불러옵니다.

```sh
claude plugin marketplace add Xia-Ataraxia/secondbrain-skills
claude plugin install secondbrain-skills@secondbrain-skills
```

그다음에는 평소 말로 시키면 됩니다. *"이 글 ingest 해줘."*

## 동작 방식

<p align="center">
  <img src="assets/demo/workflow.svg" alt="세 단계 작업 흐름: 합성 필드 노트를 살펴보고, 독립된 형식 담당 패키지를 고르고, 구조를 검증한 뒤 결과를 다시 읽는다" width="880">
</p>

<p align="center"><sub>이 저장소를 위해 그린 합성 예시이며 스크린샷이 아닙니다.</sub></p>

- **판단은 스킬이 맡습니다.** 무엇을 고르고, 어떻게 분류하고, 언제 멈출지는 Markdown에 적습니다. 스크립트는 질문 하나에만 답하고 실행을 막지 않습니다.
- **원문은 남습니다.** 자료에 대해 무엇을 쓰기 전에 먼저 Raw 노트로 원문 그대로 보존합니다.
- **형식을 안다고 써도 되는 것은 아닙니다.** 패키지는 작업이 허락한 정확한 위치에만 쓰고, 쓴 결과를 다시 읽습니다.
- **증거가 없으면 성공이 아닙니다.** 파싱은 렌더링이 아니고, 종료 코드는 쓰기의 증거가 아닙니다. 패키지는 어느 수준까지 확인했는지 밝힙니다.

## 지식 패키지

흐름은 `capture` → `inbox` → `ingest` → `query`입니다.

| 패키지 | 하는 일 |
| --- | --- |
| `capture` | 고른 탭, URL, 파일, 대화, 에이전트 세션을 Inbox 후보로 저장합니다. |
| `inbox` | Inbox 후보를 나열하고 미리 보고 센 뒤, 고른 범위를 `ingest`에 넘깁니다. |
| `ingest` | 자료 하나를 Raw 노트로 보존하고 거기서 Wiki 페이지, Map, 색인을 엮습니다. |
| `query` | 기존 노트에서 확인한 인용과 Obsidian 딥링크로 답합니다. |
| `verify` | 고른 주장을 출처와 대조합니다. |
| `audit` | 정해진 범위를 표본 조사해 품질 위험과 조사 범위를 밝힙니다. |
| `lint` | 정해진 범위의 구조, 인용, 속성, 링크를 검사합니다. |
| `status` | 개수, 밀린 양, 스냅샷 경과 시간을 읽기 전용으로 보고합니다. |
| `reindex` | 감사한 컬렉션 하나의 검색 색인을 새로 만듭니다. |
| `refresh-context` | 지정한 출처에서 에이전트 컨텍스트 스냅샷을 다시 만듭니다. |
| `onboard` | 새 볼트를 준비하거나, 기존 볼트에 더할 변경을 미리 보여줍니다. |

위 열한 개가 따르는 작업 태도는 나머지 여섯 개에 있습니다.

| 패키지 | 담는 것 |
| --- | --- |
| `principle-respect-des-fonds` | 자료를 누가 만들었고, 1차 자료인지 2차 자료인지. |
| `principle-original-order` | 원래 순서와 원문 그대로의 내용 보존. |
| `principle-hierarchical-management` | 기록을 컬렉션에서 개별 항목까지 배치하는 법. |
| `principle-collective-description` | 묶음, Map, 범위를 기술하는 법. |
| `principle-skill-creating` | 스킬이 Markdown에 둘 것과 템플릿, 얇은 스크립트, 에이전트에 넘길 것. |
| `secondbrain-mode` | 여러 패키지에 걸친 작업의 선택적 태도. 서브에이전트에 맡기고 독립 리뷰로 마칩니다. |

## Obsidian 패키지

| 패키지 | 맡는 것 |
| --- | --- |
| `obsidian-markdown` | Obsidian Flavored Markdown: 위키링크, 임베드, 콜아웃, 속성, 태그, 블록 참조. |
| `obsidian-bases` | `.base` 데이터베이스 뷰: 필터, 수식, 요약, 그룹화, 함수 레퍼런스. |
| `obsidian-canvas` | JSON Canvas `.canvas` 파일: 노드, 엣지, 좌표, 안정적인 ID. |
| `obsidian-mermaid` | 사용 중인 앱 빌드에서 실제로 렌더링되는 Mermaid 블록. |
| `obsidian-visualize` | 노트에 맞는 시각 형식 선택과 `.excalidraw.md` 장면 생성. |
| `obsidian-cli` | 공식 `obsidian` 바이너리: 읽기, 생성, 검색, 이동, 점검. |
| `obsidian-clipper` | Web Clipper 템플릿, 선택자, 변수. |
| `obsidian-doctor` | 정제된 증거로 하는 플러그인·Templater 장애 진단. |
| `obsidian-sync` | Obsidian Sync용 헤드리스 `ob` 클라이언트. |

## 설치

각 런타임의 공식 플러그인·스킬 레지스트리로 설치하고, 업데이트도 같은 경로로 합니다. 이 저장소는 설치 스크립트를 제공하지 않습니다. 플러그인과 함께 스킬 디렉터리에 복사본을 두면 복사본이 플러그인을 가립니다.

| 런타임 | 설치 | 업데이트 |
| --- | --- | --- |
| Claude Code | `claude plugin marketplace add Xia-Ataraxia/secondbrain-skills` 후 `claude plugin install secondbrain-skills@secondbrain-skills` | `claude plugin marketplace update secondbrain-skills` 후 `claude plugin update secondbrain-skills@secondbrain-skills` |
| Codex | `codex plugin marketplace add Xia-Ataraxia/secondbrain-skills` 후 `codex plugin add secondbrain-skills@secondbrain-skills` | `codex plugin marketplace upgrade secondbrain-skills` 후 `codex plugin add secondbrain-skills@secondbrain-skills` |
| GJC | `gjc plugin marketplace add Xia-Ataraxia/secondbrain-skills` 후 `gjc plugin install secondbrain-skills@secondbrain-skills` | `gjc plugin marketplace update secondbrain-skills` 후 `gjc plugin upgrade secondbrain-skills@secondbrain-skills` |
| Grok Build | `grok plugin marketplace add Xia-Ataraxia/secondbrain-skills` 후 Marketplace 탭에서 설치 | Marketplace 탭 |
| Hermes | `hermes skills tap add Xia-Ataraxia/secondbrain-skills` 후 패키지마다 `hermes skills install Xia-Ataraxia/secondbrain-skills/<name>` | 탭 |

플러그인 레지스트리가 없는 런타임(Cursor, 일반 Agent Skills)은 스킬 디렉터리의 `skills/<name>/` 폴더를 읽습니다. 그 런타임이 문서화한 가져오기 방법을 쓰십시오.

## 검증된 것

Obsidian 패키지 아홉 개는 Claude Code와 Hermes에 네이티브로 설치했고, 격리된 Obsidian 1.12.7 프로필에서 실행해 봤습니다. 지식 패키지는 로컬 형식 검사만 통과했고 런타임 로드 기록은 없습니다. Hermes에는 `v0.1.0` 태그를 설치하지 마십시오.

결과와 리비전, 한계는 모두 [docs/verification-matrix.md](docs/verification-matrix.md)에, 안전과 데이터 처리는 [docs/security-and-privacy.md](docs/security-and-privacy.md)에 있습니다.

## 저장소 구성

```
skills/<name>/SKILL.md   패키지 하나. 나머지는 모두 옆의 하위 폴더에 둡니다
docs/                    이름 규칙, 계약, 검증 매트릭스, 보안
AGENTS.md                기여자와 에이전트를 위한 저장소 계약
```

## 감사의 말

- **[구요한 (Yohan Koo)](https://github.com/johnfkoo951/cmds-llm-wiki)**, cmds-llm-wiki. 지식 패키지는 그의 명령 위에 쌓았습니다. 단계 뼈대와 섹션 이름, 용어는 그대로 두고 그 위에 소유자의 판단을 더했습니다. 무엇을 받아들이고 바꾸고 버렸는지는 각 패키지의 `references/comparison.md`에 있습니다.
- **[Andrej Karpathy](https://github.com/karpathy)**, cmds-llm-wiki가 바탕으로 삼은 LLM Wiki 패턴.
- **[Steph Ango (kepano)](https://github.com/kepano/obsidian-skills)**, obsidian-skills (MIT). `obsidian-markdown`, `obsidian-bases`, `obsidian-canvas`, `obsidian-cli`는 여기서 출발해 수정했습니다.
- **[Jonghak Seo](https://github.com/Jonghakseo/pi-extension)**, pi-extension (MIT). `obsidian-visualize`의 검사 린트와 skeleton·style 참조는 여기서 가져와 고쳤습니다.

이들의 보증이나 제휴 관계를 주장하지 않습니다. "Obsidian"은 이 스킬들이 대상으로 하는 서드파티 애플리케이션의 이름입니다.

## 라이선스

MIT. [LICENSE](LICENSE)를 참고하십시오. 원 저작물의 허가 고지는 [NOTICE](NOTICE)에, 출처 리비전과 미확정 권리 사항은 [PROVENANCE.md](PROVENANCE.md)에 있습니다. `assets/`의 그림은 직접 제작한 원본이며 [assets/asset-ledger.json](assets/asset-ledger.json)에 기록되어 있습니다.
