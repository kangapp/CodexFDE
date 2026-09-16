# Dot-source from the control repository. Keep the returned session file to resume.
param([string]$Resume, [switch]$Latest)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$l05Root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$l05Pointer = Join-Path $l05Root '.runtime/l05-practice/latest-session.txt'
if ($Latest) {
    if (-not (Test-Path -LiteralPath $l05Pointer)) { throw '尚无会话，请先执行第 1.1 节的初始化命令' }
    $Resume = (Get-Content -LiteralPath $l05Pointer -Raw -Encoding utf8).Trim()
}
if ($Resume) {
    $script:l05Session = Get-Content -LiteralPath $Resume -Raw -Encoding utf8 | ConvertFrom-Json
} else {
    $root = $l05Root
    if (-not (Test-Path -LiteralPath (Join-Path $root '.venv/Scripts/python.exe'))) { throw '请在已安装项目的控制仓库根目录运行' }
    $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
    $run = Join-Path $root ".runtime/l05-practice/$stamp"
    New-Item -ItemType Directory -Path $run | Out-Null
    $script:l05Session = [pscustomobject]@{
        control=$root; python=(Join-Path $root '.venv/Scripts/python.exe'); run=$run
        runtime=(Join-Path $root '.runtime/l04-learning'); stamp=$stamp
        actor='L05 teaching run'; gitName='L05 teaching run'; gitEmail='l05@example.invalid'
        identitySource='teaching-default-not-human-review'
    }
    $gitName = & git -C $root config user.name
    $gitEmail = & git -C $root config user.email
    if ($gitName -and $gitEmail) {
        $l05Session.actor = $gitName.Trim()
        $l05Session.gitName = $gitName.Trim()
        $l05Session.gitEmail = $gitEmail.Trim()
        $l05Session.identitySource = 'existing-git-config-not-human-review'
    }
    $script:l05Session | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'session.json') -Encoding utf8
    (Join-Path $run 'session.json') | Set-Content -LiteralPath $l05Pointer -Encoding utf8
}
$l05Control = $l05Session.control
$l05Python = $l05Session.python
$l05Run = $l05Session.run
$l05Runtime = $l05Session.runtime
$l05Actor = $l05Session.actor
$l05Examples = Join-Path $l05Control 'docs/courses/L05/examples'
$l05Fixture = Join-Path $l05Run 'ledger-fixture'
$l05ScopeRepo = Join-Path $l05Run 'scope-repo'
$l05Allow = Join-Path $l05Run 'allowed-files.json'
$l05Check = Join-Path $l05Examples 'receiving_contract_eval.py'
$l05ScopeCheck = Join-Path $l05Examples 'write_scope_eval.py'
$l05ScopeFile = Join-Path $l05ScopeRepo 'flowerp/service.py'
$l05BusinessArgs = @('-m','unittest','tests.test_l05_receiving','-v')
$l05EngineeringArgs = @('-m','unittest','tests.test_l05_scope','-v')
$l05Frozen = Join-Path $l05Run 'frozen-checks.json'
if (Test-Path -LiteralPath (Join-Path $l05Run 'scope-base.txt')) {
    $l05ScopeBase = (Get-Content -LiteralPath (Join-Path $l05Run 'scope-base.txt') -Raw -Encoding utf8).Trim()
    $l05ScopeArgs = @($l05ScopeCheck,'--repo',$l05ScopeRepo,'--base',$l05ScopeBase,'--allow-file',$l05Allow)
}
if (Test-Path -LiteralPath (Join-Path $l05Run 'prepare.json')) {
    $l05Prepare = Get-Content -LiteralPath (Join-Path $l05Run 'prepare.json') -Raw -Encoding utf8 | ConvertFrom-Json
    $l05Candidate = $l05Prepare.path
}
if (Test-Path -LiteralPath (Join-Path $l05Run 'submission.json')) {
    $l05Submission = Get-Content -LiteralPath (Join-Path $l05Run 'submission.json') -Raw -Encoding utf8 | ConvertFrom-Json
    $l05Final = $l05Submission.isolation.path
    $l05Task = $l05Submission.task.id
}
function Invoke-L05 {
    param([string]$Name, [int]$Expected, [string]$Directory, [string[]]$Command)
    $commandFile = Join-Path $l05Run ('command-' + [guid]::NewGuid().ToString('N') + '.json')
    ConvertTo-Json -InputObject @($Command) | Set-Content -LiteralPath $commandFile -Encoding utf8
    $raw = & $l05Python -B -X utf8 (Join-Path $l05Examples 'record_command.py') --cwd $Directory --evidence (Join-Path $l05Run 'evidence') --name $Name --expect $Expected --command-file $commandFile
    $wrapperExit = $LASTEXITCODE
    $record = $raw | ConvertFrom-Json
    Write-Host $record.stdout
    if ($record.stderr) { Write-Host $record.stderr }
    Write-Host "[$Name] exit=$($record.exit_code)；证据：$($record.receipt)"
    if ($wrapperExit -ne 0) { throw "退出码与预期不同；先读证据，不继续下一步：$Name" }
    return $record
}
function Invoke-L05Python {
    param([string]$Name, [int]$Expected, [string]$Directory, [string[]]$Arguments)
    Invoke-L05 $Name $Expected $Directory (@($l05Python, '-B', '-X', 'utf8') + $Arguments)
}
Write-Host "会话文件：$(Join-Path $l05Run 'session.json')"
Write-Host "控制目录：$l05Control；沿用工作台数据：$l05Runtime"
