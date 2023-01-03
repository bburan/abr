if not exist "%PREFIX%\Menu" mkdir "%PREFIX%\Menu"
copy "%RECIPE_DIR%\menu-windows.json" "%PREFIX%\Menu"
copy "%RECIPE_DIR%\abr-icon.ico" "%PREFIX%\Menu"

"%PYTHON%" -m pip install . --no-deps --ignore-installed --no-cache-dir -vvv
if errorlevel 1 exit 1
