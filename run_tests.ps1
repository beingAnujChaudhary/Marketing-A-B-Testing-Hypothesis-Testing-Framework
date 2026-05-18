Write-Host "Running test suite..." -ForegroundColor Cyan

pytest tests/ -v --tb=short

Write-Host "`nRunning coverage report..." -ForegroundColor Cyan

pytest tests/ -v --cov=src --cov-report=term-missing