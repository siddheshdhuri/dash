
echo Building Application

echo Remove existing files
RMDIR release /S /Q

MKDIR release

COPY config.yaml release\config.yaml

xcopy /s /i input release\input


SET COPYCMD=/Y

for /f %%i in ('pipenv --venv') do set VENV=%%i

pipenv run pyinstaller --paths %VENV% --hidden-import pkg_resources.py2_warn --additional-hooks-dir=src/hooks --icon=images/favicon.ico --onefile src/index.py


COPY dist\index.exe release\mtp.exe

