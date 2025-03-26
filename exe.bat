@echo off
setlocal enabledelayedexpansion

:: Check if virtual environment exists
IF NOT EXIST venv (
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate

:: Upgrade pip and install requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Clean previous builds
IF EXIST build (
    rmdir /s /q build
)
IF EXIST dist (
    rmdir /s /q dist
)

:: Build executable
pyinstaller --onefile ^
    --windowed ^
    --name "NOAARadarDownloader" ^
    --icon "radar_icon.ico" ^
    --add-data "LICENSE;." ^
    noaa_radar_downloader.py

:: Create distributable zip
powershell Compress-Archive -Path "dist\NOAARadarDownloader.exe" -DestinationPath "dist\NOAARadarDownloader.zip"

:: Deactivate virtual environment
deactivate

echo Executable created in dist folder
pause