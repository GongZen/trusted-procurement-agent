<#
    AI 협업 스크립트 공통 유틸.
    dot-source 해서 쓴다:  . "$PSScriptRoot\_common.ps1"

    핵심 아이디어 — 맥락을 세션에 쌓지 않고 저장소에 외재화한다.
    각 AI는 매번 새 세션으로 시작하므로, 사람이 "진행 상황 확인해"라고
    말하는 대신 스크립트가 브리핑을 만들어 지시문 앞에 붙인다.
#>

$script:RepoSlug = 'GongZen/trusted-procurement-agent'

function Get-RepoSlug { $script:RepoSlug }

# ── 검토자 계정 토큰 ─────────────────────────────────────────────
# 같은 GitHub 계정으로는 자기 PR을 승인할 수 없다. 작업자와 검토자의
# 계정을 분리해야 approve / request-changes 가 실제로 등록된다.
function Get-AgentToken {
    param([string]$TokenPath = "$HOME\.codex-gh-token")

    if (-not (Test-Path $TokenPath)) {
        throw "계정 토큰 파일이 없습니다: $TokenPath"
    }
    $t = (Get-Content $TokenPath -Raw).Trim()
    if ($t.Length -lt 20) { throw "토큰이 비어 있거나 형식이 올바르지 않습니다." }
    return $t
}

# ── 검토자 계정 검증 ─────────────────────────────────────────────
# GitHub는 자기 PR에 대한 승인·변경요청을 거부한다. 실행 직전에 실제 계정을
# 확인해, 기대와 다르면 리뷰가 등록되지 않는 상태로 진행하지 않는다.
function Confirm-ReviewerAccount {
    param(
        [Parameter(Mandatory = $true)][string]$Expected,
        [Parameter(Mandatory = $true)][string]$PrAuthor,
        [string]$Token
    )

    $prev = $env:GH_TOKEN
    if ($Token) { $env:GH_TOKEN = $Token }
    try {
        $actual = gh api user | ConvertFrom-Json | Select-Object -ExpandProperty login
    }
    finally {
        if ($Token) {
            if ($prev) { $env:GH_TOKEN = $prev } else { Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue }
        }
    }

    if ($actual -ne $Expected) {
        throw "검토자 계정이 기대와 다릅니다. 기대=$Expected, 실제=$actual. 토큰 설정을 확인하세요."
    }
    if ($actual -eq $PrAuthor) {
        throw "자기 PR은 검토할 수 없습니다. PR 작성자=$PrAuthor, 검토자=$actual."
    }

    Write-Host "검토자 계정 확인: $actual (PR 작성자: $PrAuthor)" -ForegroundColor Cyan
    return $actual
}

# ── 진행 상황 브리핑 ─────────────────────────────────────────────
# 어느 AI가 언제 들어와도 같은 맥락을 얻게 하는 장치.
function Get-RepoBriefing {
    param([string]$RepoRoot)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('# 현재 진행 상황 (스크립트가 자동 생성)')
    $lines.Add('')

    $lines.Add('## 열린 Issue — 미완료 작업이다')
    $issues = gh issue list --state open --limit 30 --json number,title,assignees | ConvertFrom-Json
    if ($issues.Count -eq 0) { $lines.Add('- 없음') }
    else { foreach ($i in $issues) { $lines.Add("- #$($i.number) $($i.title)") } }
    $lines.Add('')

    $lines.Add('## 열린 PR — 검토 대기 또는 진행 중')
    $prs = gh pr list --state open --limit 30 --json number,title,author,reviewDecision,headRefName | ConvertFrom-Json
    if ($prs.Count -eq 0) { $lines.Add('- 없음') }
    else {
        foreach ($p in $prs) {
            $d = if ($p.reviewDecision) { $p.reviewDecision } else { '검토 없음' }
            $lines.Add("- #$($p.number) $($p.title)  [작성: $($p.author.login) / 판정: $d / 브랜치: $($p.headRefName)]")
        }
    }
    $lines.Add('')

    $lines.Add('## 최근 커밋 — 완료된 과거')
    $log = git -C $RepoRoot log --oneline -10
    foreach ($l in $log) { $lines.Add("- $l") }
    $lines.Add('')

    $lines.Add('## 최근 닫힌 Issue — 이미 끝난 일이니 다시 제안하지 않는다')
    $closed = gh issue list --state closed --limit 5 --json number,title | ConvertFrom-Json
    if ($closed.Count -eq 0) { $lines.Add('- 없음') }
    else { foreach ($i in $closed) { $lines.Add("- #$($i.number) $($i.title)") } }
    $lines.Add('')

    $lines.Add('## 문서 지도 — 판단 전에 관련 문서를 직접 읽는다')
    $lines.Add('- `COLLABORATION.md` 0절 — **진행 상황. 새 세션은 여기부터 읽는다**')
    $lines.Add('- `README.md` — 문제 정의(식자재 조달 점검 우선순위), 답하지 않는 것')
    $lines.Add('- `DATA_CRITERIA.md` — 데이터 선정 조건과 실측 판정. **데이터 관련 판단은 여기가 기준이다**')
    $lines.Add('- `Scaffolding.md` — 진행 단계와 잠가야 할 결정 영역. **결정 관련 판단은 여기가 기준이다**')
    $lines.Add('- `DECISIONS.md` — 이미 내려진 결정과 폐기된 결정의 경계. 번복하려면 근거가 필요하다')
    $lines.Add('- `DATA_SOURCES.md` — API 엔드포인트·파라미터·재현 절차')
    $lines.Add('- `_local/Skillthon.md` — 대회 요건. 배점·심사 방식·제출물 (로컬 전용)')
    $lines.Add('')
    $lines.Add('> 현재 정의: 식자재 조달 점검 우선순위를 정하는 Agent. 데이터는 공공데이터포털 API 13종.')
    $lines.Add('> `PROJECT_BRIEF.md`와 `analysis/measure_premises.py`는 삭제됐다. 링크가 보이면 오래된 참조다.')
    $lines.Add('')

    return ($lines -join "`n")
}

# ── 에이전트 실행 ────────────────────────────────────────────────
function Invoke-Agent {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('claude', 'codex')][string]$Agent,
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)][string]$LogFile,
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [string]$Token
    )

    if ($Token) { $env:GH_TOKEN = $Token }

    # 에이전트는 진행 상황을 stderr로 출력한다. ErrorActionPreference가 Stop이면
    # 첫 줄에서 중단되므로 이 구간만 Continue로 되돌린다.
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    Push-Location $RepoRoot
    try {
        if ($Agent -eq 'codex') {
            # inherit=all — Codex가 실행하는 gh 명령에도 GH_TOKEN이 전달되어야
            # 검토자 계정으로 리뷰가 남는다.
            $a = @(
                'exec',
                '-s', 'danger-full-access',
                '-c', 'shell_environment_policy.inherit=all',
                '-C', $RepoRoot,
                $Prompt
            )
            & codex @a 2>&1 | Tee-Object -FilePath $LogFile
        }
        else {
            $a = @(
                '-p', $Prompt,
                '--permission-mode', 'acceptEdits',
                '--allowedTools', 'Bash Read Grep Glob Edit Write'
            )
            & claude @a 2>&1 | Tee-Object -FilePath $LogFile
        }
    }
    finally {
        Pop-Location
        $ErrorActionPreference = $prevEAP
        if ($Token) { Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue }
    }
}

# ── 로그 파일 경로 ───────────────────────────────────────────────
function New-LogPath {
    param([string]$RepoRoot, [string]$Tag)

    $dir = Join-Path $RepoRoot 'logs'
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    return (Join-Path $dir "$Tag-$stamp.log")
}
