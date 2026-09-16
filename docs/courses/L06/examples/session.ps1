param([string]$Resume)
$ErrorActionPreference='Stop'
if($Resume){$l06Session=Get-Content -LiteralPath $Resume -Raw -Encoding utf8 | ConvertFrom-Json}
else {
 $root=(Get-Location).Path
 $python=Join-Path $root '.venv/Scripts/python.exe'
 if(-not(Test-Path -LiteralPath $python)){throw '请在已安装项目的控制仓库根目录执行'}
 $stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
 $run=Join-Path $root ('.runtime/l06-practice/'+$stamp)
 New-Item -ItemType Directory $run | Out-Null
 $l06Session=[pscustomobject]@{control=$root;python=$python;run=$run;runtime=(Join-Path $root '.runtime/l04-learning');stamp=$stamp}
 $l06Session | ConvertTo-Json | Set-Content (Join-Path $run 'session.json') -Encoding utf8
}
$l06Control=$l06Session.control;$l06Python=$l06Session.python;$l06Run=$l06Session.run;$l06Runtime=$l06Session.runtime
$l06Actor=$l06Session.actor;$l06Examples=Join-Path $l06Control 'docs/courses/L06/examples'
$l06Recorder=Join-Path $l06Control 'docs/courses/L05/examples/record_command.py'
$l06Frozen=Join-Path $l06Run 'frozen-checks.json';$l06Allow=Join-Path $l06Run 'allowed-files.json'
if(Test-Path (Join-Path $l06Run 'prepare.json')){$l06Prepare=Get-Content (Join-Path $l06Run 'prepare.json') -Raw -Encoding utf8 | ConvertFrom-Json;$l06Candidate=$l06Prepare.path}
if(Test-Path (Join-Path $l06Run 'session-ref.txt')){$l06SessionRef=(Get-Content (Join-Path $l06Run 'session-ref.txt') -Raw).Trim()}
if(Test-Path (Join-Path $l06Run 'submission.json')){$l06Submission=Get-Content (Join-Path $l06Run 'submission.json') -Raw -Encoding utf8 | ConvertFrom-Json;$l06Final=$l06Submission.isolation.path;$l06Task=$l06Submission.task.id}
function Invoke-L06 {
 param([string]$Name,[int]$Expected,[string]$Directory,[string[]]$Command)
 $raw=& $l06Python -B -X utf8 $l06Recorder --cwd $Directory --evidence (Join-Path $l06Run 'evidence') --name $Name --expect $Expected -- @Command
 $exit=$LASTEXITCODE;$record=$raw | ConvertFrom-Json
 Write-Host $record.stdout
 if($record.stderr){Write-Host $record.stderr}
 Write-Host "[$Name] exit=$($record.exit_code)；证据：$($record.receipt)"
 if($exit -ne 0){throw "退出码不符，先读取证据：$Name"}
 return $record
}
function Invoke-L06Python {
 param([string]$Name,[int]$Expected,[string]$Directory,[string[]]$Arguments)
 Invoke-L06 $Name $Expected $Directory (@($l06Python,'-B','-X','utf8')+$Arguments)
}
function New-L06Report {
 param([string]$Name)
 $folder=Join-Path $l06Run 'reports'
 New-Item -ItemType Directory -Force $folder | Out-Null
 return (Join-Path $folder ($Name+'-'+[guid]::NewGuid().ToString('N')+'.json'))
}
Write-Host "会话文件：$(Join-Path $l06Run 'session.json')"
Write-Host "控制目录：$l06Control；运行目录：$l06Runtime"
