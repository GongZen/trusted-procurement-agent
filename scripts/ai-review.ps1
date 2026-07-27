<#
.SYNOPSIS
    상대 AI에게 PR 교차 검토를 맡기고, 그 과정을 로그로 남긴다.

.DESCRIPTION
    작업자와 검토자를 반드시 다른 GitHub 계정으로 분리한다. 같은 계정이면
    GitHub가 자기 PR에 대한 승인·변경요청을 거부해 판정이 코멘트로만 남는다.

    - Claude가 만든 PR(GongZen 명의)  → Codex가 검토(Sub-GongZen 토큰 주입)
    - Codex가 만든 PR(Sub-GongZen 명의) → Claude가 검토(기본 로그인 사용)

    검토자에게는 지시문 앞에 저장소 브리핑을 자동으로 붙여, 매번 새 세션으로
    시작하는 AI가 사람의 설명 없이도 현재 맥락을 얻게 한다.

.PARAMETER PR
    검토할 PR 번호.

.PARAMETER Agent
    검토자. 생략하면 PR 작성자를 보고 반대쪽을 자동 선택한다.

.PARAMETER Issue
    판정 기준이 되는 Issue 번호. 생략하면 PR 본문의 "Closes #N"에서 찾는다.

.EXAMPLE
    ./scripts/ai-review.ps1 -PR 2
    ./scripts/ai-review.ps1 -PR 5 -Agent claude
#>
param(
    [Parameter(Mandatory = $true)][int]$PR,
    [ValidateSet('claude', 'codex')][string]$Agent,
    [int]$Issue = 0
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"
$repoRoot = Split-Path -Parent $PSScriptRoot

# ── 1. PR 정보 ────────────────────────────────────────────────────
# PowerShell 변수는 대소문자를 구분하지 않는다. $pr 로 받으면 파라미터 $PR을
# 덮어써서 타입 오류가 난다. 반드시 다른 이름을 쓴다.
$prInfo = gh pr view $PR --json body,author,headRefName,title | ConvertFrom-Json
$prAuthor = $prInfo.author.login

# ── 2. 검토자 결정 — 작성자와 반대쪽 ─────────────────────────────
if (-not $Agent) {
    # Sub-GongZen 명의 PR은 Codex가 만든 것이므로 Claude가 검토한다.
    $Agent = if ($prAuthor -eq 'Sub-GongZen') { 'claude' } else { 'codex' }
    Write-Host "검토자를 자동 선택했습니다: $Agent (PR 작성자: $prAuthor)"
}
# 각 에이전트가 사용할 계정을 명시적으로 고정한다.
#   Codex  → Sub-GongZen (토큰 파일 주입)
#   Claude → GongZen     (기본 로그인. 주변 GH_TOKEN이 남아 있으면 제거해야 한다)
$expectedAccount = if ($Agent -eq 'codex') { 'Sub-GongZen' } else { 'GongZen' }

if ($expectedAccount -eq $prAuthor) {
    Write-Error "자기 PR은 검토할 수 없습니다. PR 작성자=$prAuthor, 검토자 계정=$expectedAccount. 반대쪽 에이전트를 지정하세요."
    exit 1
}

if ($Agent -eq 'codex') {
    $token = Get-AgentToken
}
else {
    # Claude는 keyring 로그인을 써야 한다. 이전 실행이 남긴 GH_TOKEN이 있으면
    # 엉뚱한 계정으로 리뷰가 등록되므로 반드시 지운다.
    $token = $null
    if ($env:GH_TOKEN) {
        Write-Host "주변 GH_TOKEN을 제거합니다 (Claude는 기본 로그인을 사용)" -ForegroundColor DarkGray
        Remove-Item Env:GH_TOKEN
    }
}

# 실제로 어느 계정이 붙는지 확인한다. 기대와 다르면 리뷰 등록이 거부되므로 미리 멈춘다.
$actual = Confirm-ReviewerAccount -Expected $expectedAccount -PrAuthor $prAuthor -Token $token

# ── 3. 판정 기준 Issue ────────────────────────────────────────────
if ($Issue -eq 0) {
    if ($prInfo.body -match 'Closes\s+#(\d+)') {
        $Issue = [int]$Matches[1]
        Write-Host "판정 기준 Issue를 PR 본문에서 찾았습니다: #$Issue"
    }
    else {
        Write-Error "PR #$PR 본문에 'Closes #N'이 없습니다. -Issue 로 직접 지정하세요."
        exit 1
    }
}

# ── 4. 라운드 계산 ────────────────────────────────────────────────
# 라운드 상한을 두지 않으면 검토가 끝나지 않는다. 실제로 한 PR에서
# 4라운드까지 반복되며 프로젝트가 멈춘 전례가 있다.
$existing = gh pr view $PR --json reviews | ConvertFrom-Json
$round = $existing.reviews.Count + 1
$prevReview = if ($existing.reviews.Count -gt 0) { $existing.reviews[-1].body } else { $null }

$roundRule = if ($round -ge 3) {
    @"
**이번이 ${round}라운드다. 라운드 상한(2회)을 넘었다.**
남은 지적은 blocker로 올리지 말고 후속 Issue 제안으로 적은 뒤 --approve 하라.
단 아래 '항상 blocker인 것'에 해당하면 라운드 수와 무관하게 --request-changes 다.
"@
}
else {
    "이번이 ${round}라운드다. 라운드 상한은 2회이니 이번에 지적할 것을 모두 지적하라."
}

$prevRule = if ($prevReview) {
    @"

## 이전 라운드 검토 결과 (재지적 금지 대상)

아래는 직전 검토에서 네가 남긴 판정이다. **여기서 해소 판정된 항목을 다시 blocker로 올리지 마라.**
수정이 불완전하더라도 원래 지적의 핵심이 해소됐으면 consider로 내려라.

$prevReview
"@
}
else { "" }

# ── 5. 지시문 = 브리핑 + 검토 규칙 ────────────────────────────────
$guide = if ($Agent -eq 'codex') { 'CODEX.md' } else { 'CLAUDE.md' }
$briefing = Get-RepoBriefing -RepoRoot $repoRoot

$prompt = @"
$briefing
$prevRule

---

# 지시 — PR ${PR}번 교차 검토

프로젝트 루트의 $guide 를 먼저 읽고, 특히 '검토자로서의 판정 기준' 절을 그대로 적용하라.

아래를 실행해 내용을 확인하라.
- gh issue view $Issue   (판정 기준이 되는 완료 조건)
- gh pr diff $PR         (실제 변경 내용)
- gh pr view $PR         (작성자의 자체 판정)

## 검토의 목적

문서를 완벽하게 만드는 것이 아니라, **다음 단계를 안전하게 시작할 수 있게 만드는 것**이다.

## 판정 규칙

1. Issue ${Issue}번의 완료 조건을 항목별로 충족 또는 미충족으로 판정하고, 각 항목에 근거를 한 줄씩 붙여라.
2. **blocker의 정의를 좁게 잡아라** — 이 상태로 다음 Step을 시작하면 실제로 막히거나, 잘못된 산출물이 나오거나, 되돌리기 어려운 피해가 생기는 것만 blocker다.
   판정 전에 스스로 물어라: *이걸 안 고치고 다음 단계로 가면 구체적으로 무엇이 잘못되는가?* 구체적으로 답할 수 없으면 blocker가 아니다.
3. **표현 불일치·문언상 충돌·더 명확히 쓸 수 있는 부분은 consider 이하로 내려라.** 이런 유형만으로 PR을 막지 마라.
4. **완료 조건에 없는 새 기준을 만들어 미충족 판정하지 마라.** 더 나은 방향이 보이면 후속 Issue 제안으로 적어라.
5. 형식적 승인은 하지 마라. 위 규칙은 기준을 낮추는 것이 아니라 **기준의 대상을 좁히는 것**이다.

$roundRule

## 항상 blocker인 것 (라운드 수와 무관)

- 공개 범위 규칙 위반
- 같은 입력에 다른 결과가 나오는 것
- 사람을 기다리며 루프가 멈추는 설계
- 데이터가 뒷받침하지 못하는 수치·용어 사용
- 플랫폼 독립성 규칙 위반 ($guide 참조)

## 마무리

gh pr review $PR 로 결과를 남겨라. blocker가 있으면 --request-changes, 없으면 --approve 다.
모든 산출물은 한국어로 작성하라.
"@

# ── 5. 실행 ───────────────────────────────────────────────────────
$logFile = New-LogPath -RepoRoot $repoRoot -Tag "review-PR$PR-$Agent"

Write-Host ""
Write-Host "PR #$PR 검토 시작 — 검토자: $Agent / 기준: Issue #$Issue" -ForegroundColor Cyan
Write-Host "로그: $logFile"
Write-Host ""

Invoke-Agent -Agent $Agent -Prompt $prompt -LogFile $logFile -RepoRoot $repoRoot -Token $token

# ── 6. 결과 요약 ──────────────────────────────────────────────────
Write-Host ""
Write-Host "=== 검토 결과 ===" -ForegroundColor Cyan
$after = gh pr view $PR --json reviews,reviewDecision | ConvertFrom-Json
if ($after.reviews.Count -eq 0) {
    Write-Host "리뷰가 남지 않았습니다. 로그를 확인하세요." -ForegroundColor Yellow
}
else {
    $last = $after.reviews[-1]
    Write-Host "판정: $($last.state)   (PR 전체 판정: $($after.reviewDecision))"
    Write-Host "검토자: $($last.author.login)"
}
Write-Host "PR: https://github.com/$(Get-RepoSlug)/pull/$PR"
Write-Host "전체 과정: $logFile"
