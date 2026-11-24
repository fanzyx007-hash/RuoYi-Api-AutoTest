# run-test.ps1 - 一条命令跑完压测并生成 HTML 报告
# 用法:
#   .\run-test.ps1 -Jmx "D:\DSH workplace\perf\ruoyi-soak.jmx"
#   .\run-test.ps1 -Jmx "...\ruoyi-mix.jmx" -Jtl "...\mix.jtl" -Report "...\report_mix"

param(
    [Parameter(Mandatory = $true)][string]$Jmx,
    [string]$Jtl = "",
    [string]$Report = "",
    [string]$Props = "D:\DSH workplace\perf\report.properties",
    [string]$JmeterHome = "D:\apache-jmeter-5.6.3"
)

$ErrorActionPreference = "Stop"

$base = [System.IO.Path]::GetFileNameWithoutExtension($Jmx) -replace '^ruoyi-', ''
if (-not $Jtl)    { $Jtl    = Join-Path (Split-Path $Jmx) "$base.jtl" }
if (-not $Report) { $Report = Join-Path (Split-Path $Jmx) "report_$base" }

$jmeter = Join-Path $JmeterHome "bin\jmeter.bat"
if (-not (Test-Path $jmeter)) { throw "找不到 JMeter: $jmeter" }
if (-not (Test-Path $Jmx))    { throw "找不到脚本: $Jmx" }

Write-Host "== 1/3 清理旧数据 ==" -ForegroundColor Cyan
if (Test-Path $Jtl)    { Remove-Item -LiteralPath $Jtl -Force;    Write-Host "  已删除 $Jtl" }
if (Test-Path $Report) { Remove-Item -LiteralPath $Report -Recurse -Force; Write-Host "  已删除 $Report" }

Write-Host "== 2/3 执行压测 ==" -ForegroundColor Cyan
Write-Host "  $Jmx -> $Jtl"
& $jmeter -n -t $Jmx -l $Jtl -j (Join-Path (Split-Path $Jtl) "$base.log")
if ($LASTEXITCODE -ne 0) { throw "压测失败，退出码 $LASTEXITCODE（看 $(Join-Path (Split-Path $Jtl) "$base.log")）" }

$rows = (Get-Content -LiteralPath $Jtl | Measure-Object -Line).Lines - 1
Write-Host "  样本数 $rows" -ForegroundColor Green

Write-Host "== 3/3 生成报告 ==" -ForegroundColor Cyan
& $jmeter -g $Jtl -o $Report -p $Props
if ($LASTEXITCODE -ne 0) { throw "报告生成失败，退出码 $LASTEXITCODE" }

$statsFile = Join-Path $Report "statistics.json"
if (Test-Path $statsFile) {
    $t = (Get-Content -LiteralPath $statsFile -Raw -Encoding UTF8 | ConvertFrom-Json).total
    Write-Host ""
    Write-Host "  样本 $($t.sampleCount) | 错误 $($t.errorCount) ($($t.errorPct)%) | 吞吐 $([math]::Round($t.throughput,2))/s" -ForegroundColor Green
    Write-Host "  平均 $([math]::Round($t.meanResTime,1))ms | P90 $([math]::Round($t.pct1ResTime)) | P95 $([math]::Round($t.pct2ResTime)) | P99 $([math]::Round($t.pct3ResTime))ms | max $($t.maxResTime)ms"
}
Write-Host ""
Write-Host "报告: $(Join-Path $Report 'index.html')" -ForegroundColor Yellow
