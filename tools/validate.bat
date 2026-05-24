@echo off
REM Convenience wrapper so you can run `tools\validate` (or double-click this
REM file) on Windows without typing the full Python path. Forwards any args
REM (e.g. an explicit index.html path) to the validator. %~dp0 = this folder.
py "%~dp0validate.py" %*
