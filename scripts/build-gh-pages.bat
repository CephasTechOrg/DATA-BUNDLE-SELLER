@echo off
REM Build docs/ for GitHub Pages. Run from repo root: scripts\build-gh-pages.bat

cd /d "%~dp0\.."
if not exist "frontend\index.html" (
    echo Error: Run from repo root. frontend\index.html not found.
    pause
    exit /b 1
)

if exist "docs" rmdir /s /q "docs"
mkdir "docs"

copy "frontend\index.html" "docs\"
if exist "frontend\style" xcopy "frontend\style" "docs\style\" /e /i /y >nul
if exist "frontend\js" xcopy "frontend\js" "docs\js\" /e /i /y >nul
if exist "frontend\images" xcopy "frontend\images" "docs\images\" /e /i /y >nul

mkdir "docs\admin" 2>nul
copy "admin\index.html" "docs\admin\"
copy "admin\style.css" "docs\admin\"
copy "admin\app.js" "docs\admin\"

echo.
echo Built site in: docs\
echo   - Customer: docs\index.html, docs\style\, docs\js\, docs\images\
echo   - Admin:    docs\admin\
echo.
echo Next: Commit and push. In GitHub: Settings ^> Pages ^> Source: branch main, folder /docs
