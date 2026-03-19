@echo off
setlocal
set "PYTHONPATH=%~dp0src;%~dp0.deps"
python -m pcbai.pipeline.cli %*
