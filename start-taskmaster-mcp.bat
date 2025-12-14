@echo off
cd /d "C:\buildgame\sanguo"
REM 从系统环境变量继承 API 密钥（使用 OpenAI 与 newguild 保持一致）
set OPENAI_API_KEY=%OPENAI_API_KEY%
set ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%
set PERPLEXITY_API_KEY=%PERPLEXITY_API_KEY%
npx -y task-master-ai
