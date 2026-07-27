<#
.SYNOPSIS
    Issue 하나를 AI에게 배정해 작업 → 커밋 → PR 생성까지 맡긴다.

.DESCRIPTION
    지시문 앞에 저장소 브리핑을 자동으로 붙인다. 각 AI는 매번 새 세션으로
    시작하므로, 사람이 "진행 상황을 확인해"라고 설명하는 대신 스크립트가
    현재 상태(열린 Issue·PR·최근 커밋·문서 지도)를 주입한다.

    Codex에게 배정하면 PR이 Sub-GongZen 명의로 생성되어, 이후 Claude가
    검토자로서 approve / request-changes 를 실제로 남길 수 있다.

.PARAMETER Issue
    작업할 Issue 번호.

.PARAMETER Agent
    작업자. 기본값은 codex (Claude는 보통 대화 세션에서 직접 작업한다).

.PARAMETER Branch
    작업 브랜치 이름. 생략하면 issue-<번호> 로 만든다.

.EXAMPLE
    ./scripts/ai-work.ps1 -Issue 3
    ./scripts/ai-work.ps1 -Issue 3 -Branch feat/kpi-lock
#>
param(
    [Parameter(Mandatory = $true)][int]$Issue,
    [ValidateSet('claude', 'codex')][string]$Agent = 'codex',
    [string]$Branch
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"
$repoRoot = Split-Path -Parent $PSScriptRoot

# ── 1. Issue 확인 ─────────────────────────────────────────────────
$iss = gh issue view $Issue --json title,state | ConvertFrom-Json
if ($iss.state -ne 'OPEN') {
    Write-Error "Issue #$Issue 은 이미 $($iss.state) 상태입니다."
    exit 1
}
Write-Host "작업 대상: #$Issue $($iss.title)"

if (-not $Branch) { $Branch = "issue-$Issue" }

# ── 2. 계정 분리 ──────────────────────────────────────────────────
# Codex가 만든 PR은 Sub-GongZen 명의여야 Claude가 검토자로 판정을 남길 수 있다.
$token = if ($Agent -eq 'codex') { Get-AgentToken } else { $null }

# ── 3. 지시문 = 브리핑 + 작업 규칙 ────────────────────────────────
$guide = if ($Agent -eq 'codex') { 'CODEX.md' } else { 'CLAUDE.md' }
$briefing = Get-RepoBriefing -RepoRoot $repoRoot

$prompt = @"
$briefing

---

# 지시 — Issue ${Issue}번 작업

프로젝트 루트의 $guide 를 먼저 읽고 그 지침에 따라 행동하라.
그다음 gh issue view $Issue 로 지시와 완료 조건을 확인하라.

작업 규칙:
1. Issue의 **완료 조건을 전부 충족**시켜라. 하나라도 못 지켰으면 PR 본문에 미충족으로 정직하게 적어라.
2. Issue의 **범위 밖 항목은 건드리지 마라.** 범위를 넓히지 않는다.
3. 결정이 필요해지면 그 자리에서 판단하지 말고 Scaffolding.md의 결정 목록(D1~D13)을 확인하라. 거기에 없는 새 결정이 필요하면 **작업을 멈추고 PR 본문에 그 사실을 적어라.**
4. 공개 저장소에 올라가는 파일에는 공개 범위 규칙을 위반하는 표현을 넣지 마라. 판정 기준은 $guide 에 있다.
5. 모든 산출물은 한국어로 작성하라.

작업 절차:
- git checkout -b $Branch  (main에서 분기)
- 파일을 수정하고 의미 있는 단위로 커밋한다. 커밋 메시지는 한국어로 무엇을 왜 바꿨는지 쓴다.
- git push -u origin $Branch
- gh pr create 로 PR을 만든다. base는 main이다.
- PR 본문에는 반드시 다음을 포함한다.
  - Closes #$Issue
  - 완료 조건을 표로 옮기고 각 항목을 스스로 충족/미충족 판정 + 근거
  - 판단이 갈릴 수 있는 곳 (없으면 없음이라고 쓴다)

main 브랜치에 직접 커밋하거나 push하지 마라. 보호 규칙으로 거부된다.
"@

# ── 4. 실행 ───────────────────────────────────────────────────────
$logFile = New-LogPath -RepoRoot $repoRoot -Tag "work-issue$Issue-$Agent"

Write-Host ""
Write-Host "Issue #$Issue 작업 시작 — 작업자: $Agent / 브랜치: $Branch" -ForegroundColor Cyan
Write-Host "로그: $logFile"
Write-Host ""

Invoke-Agent -Agent $Agent -Prompt $prompt -LogFile $logFile -RepoRoot $repoRoot -Token $token

# ── 5. 결과 요약 ──────────────────────────────────────────────────
Write-Host ""
Write-Host "=== 작업 결과 ===" -ForegroundColor Cyan
$prs = gh pr list --state open --head $Branch --json number,title,author | ConvertFrom-Json
if ($prs.Count -eq 0) {
    Write-Host "PR이 생성되지 않았습니다. 로그를 확인하세요." -ForegroundColor Yellow
}
else {
    $p = $prs[0]
    Write-Host "PR #$($p.number) 생성됨 — 작성자: $($p.author.login)"
    Write-Host "https://github.com/$(Get-RepoSlug)/pull/$($p.number)"
    Write-Host ""
    $reviewer = if ($Agent -eq 'codex') { 'claude' } else { 'codex' }
    Write-Host "다음: ./scripts/ai-review.ps1 -PR $($p.number) -Agent $reviewer" -ForegroundColor Green
}
Write-Host "전체 과정: $logFile"
