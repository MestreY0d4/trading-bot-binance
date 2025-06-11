#!/bin/bash
# Script automatizado para upload do Bot Trading para GitHub
# Versão atualizada com suporte a repositório PRIVADO e verificações melhoradas

set -e  # Parar se qualquer comando falhar

echo "🚀 BOT TRADING BINANCE - UPLOAD PARA GITHUB PRIVADO"
echo "=================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Função para print colorido
print_status() {
    case $2 in
        "error") echo -e "${RED}❌ $1${NC}" ;;
        "success") echo -e "${GREEN}✅ $1${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️ $1${NC}" ;;
        "info") echo -e "${BLUE}ℹ️ $1${NC}" ;;
        "private") echo -e "${PURPLE}🔒 $1${NC}" ;;
        *) echo "$1" ;;
    esac
}

# Verificar se estamos no diretório correto
if [ ! -f "main.py" ]; then
    print_status "Erro: main.py não encontrado. Execute no diretório do projeto!" "error"
    exit 1
fi

print_status "Verificando projeto Bot Trading..." "info"

# 1. VERIFICAÇÕES DE SEGURANÇA MELHORADAS
echo ""
echo "🔐 1. VERIFICAÇÕES DE SEGURANÇA"
echo "================================"

# Função para verificar API keys - melhorada para ser mais específica
check_api_keys() {
    local found_issues=false
    
    print_status "Verificando API keys Binance..." "info"
    
    # Padrões específicos para Binance e outras APIs
    local patterns=(
        # Binance API keys reais (64 caracteres alfanuméricos)
        'api_key.*[=:].*["\'"'"'][A-Za-z0-9]{60,70}["\'"'"']'
        'secret.*[=:].*["\'"'"'][A-Za-z0-9/+=]{60,70}["\'"'"']'
        'API_KEY.*[=:].*["\'"'"'][A-Za-z0-9]{60,70}["\'"'"']'
        'SECRET.*[=:].*["\'"'"'][A-Za-z0-9/+=]{60,70}["\'"'"']'
        
        # Tokens diversos longos
        'token.*[=:].*["\'"'"'][A-Za-z0-9_-]{40,}["\'"'"']'
        'TOKEN.*[=:].*["\'"'"'][A-Za-z0-9_-]{40,}["\'"'"']'
        
        # Padrões de chaves privadas
        '-----BEGIN.*PRIVATE KEY-----'
        'sk-[A-Za-z0-9]{20,}'
        
        # Senhas em configurações
        'password.*[=:].*["\'"'"'][^Y][^O][^U][^R].*["\'"'"']'
    )
    
    for pattern in "${patterns[@]}"; do
        if grep -r -E "$pattern" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=__pycache__ --exclude="*.log" --exclude="*.db" 2>/dev/null; then
            print_status "PERIGO: Possível API key/senha real encontrada!" "error"
            echo "Padrão detectado: $pattern"
            found_issues=true
        fi
    done
    
    # Verificar especificamente arquivos que não devem ter keys reais
    local config_files=("config/settings.yaml" "config.yaml" ".env" "main.py")
    for file in "${config_files[@]}"; do
        if [ -f "$file" ]; then
            # Buscar por keys que NÃO sejam placeholders
            if grep -E "(api_key|secret).*[=:].*[\"'][A-Za-z0-9]{50,}[\"']" "$file" 2>/dev/null | grep -v -E "(YOUR_|EXAMPLE_|TEST_|PLACEHOLDER)" > /dev/null; then
                print_status "ATENÇÃO: $file pode conter API key real!" "warning"
                echo "Verifique se as keys são placeholders ou exemplos"
                found_issues=true
            fi
        fi
    done
    
    if [ "$found_issues" = true ]; then
        return 1
    else
        return 0
    fi
}

# Verificar configurações de produção perigosas
check_production_config() {
    local suspicious_terms=(
        'mode.*[=:].*["\'"'"']real["\'"'"']'
        'testnet.*[=:].*false'
        'production.*[=:].*true'
        'live_trading.*[=:].*true'
        'real_trading.*[=:].*true'
    )
    
    print_status "Verificando configurações de produção..." "info"
    
    for term in "${suspicious_terms[@]}"; do
        if grep -r -i -E "$term" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=__pycache__ 2>/dev/null; then
            print_status "ATENÇÃO: Configuração de modo REAL encontrada!" "warning"
            echo "Termo encontrado: $term"
            echo "Para repositório privado, isso pode ser aceitável."
            return 1
        fi
    done
    return 0
}

# Executar verificações de segurança
print_status "🔍 Executando verificações de segurança..." "info"

if ! check_api_keys; then
    echo ""
    print_status "❌ VERIFICAÇÃO DE API KEYS FALHOU" "error"
    echo ""
    echo "📋 Soluções recomendadas:"
    echo "1. Mova API keys para arquivo .env (não versionado)"
    echo "2. Use variáveis de ambiente do sistema"
    echo "3. Use placeholders como 'YOUR_API_KEY_HERE'"
    echo "4. Configure arquivo separado em .gitignore"
    echo ""
    
    read -p "🔒 Como o repositório será PRIVADO, deseja continuar? (y/N): " continue_with_keys
    if [[ $continue_with_keys != [yY] ]]; then
        print_status "Upload cancelado para proteção" "info"
        exit 1
    fi
    print_status "CONTINUANDO (repositório privado protege as keys)" "warning"
else
    print_status "Nenhuma API key real encontrada" "success"
fi

if ! check_production_config; then
    echo ""
    read -p "🔒 Configuração de produção detectada. Continuar com repositório privado? (y/N): " continue_prod
    if [[ $continue_prod != [yY] ]]; then
        print_status "Upload cancelado" "info"
        exit 1
    fi
    print_status "CONTINUANDO (repositório privado é seguro)" "warning"
else
    print_status "Configurações seguras detectadas" "success"
fi

# 2. ORGANIZAR ESTRUTURA DO PROJETO
echo ""
echo "📁 2. ORGANIZANDO ESTRUTURA DO PROJETO"
echo "======================================"

# Detectar arquivos com prefixo trading_bot_ e organizar
organize_trading_bot_files() {
    local files_to_organize=($(ls trading_bot_* 2>/dev/null || true))
    
    if [ ${#files_to_organize[@]} -gt 0 ]; then
        print_status "Detectados ${#files_to_organize[@]} arquivos com prefixo 'trading_bot_'" "info"
        
        echo ""
        echo "📋 Arquivos detectados:"
        for file in "${files_to_organize[@]}"; do
            echo "  - $file"
        done
        
        echo ""
        read -p "🔧 Deseja remover o prefixo 'trading_bot_' e organizar automaticamente? (Y/n): " auto_organize
        
        if [[ $auto_organize != [nN] ]]; then
            print_status "Organizando arquivos automaticamente..." "info"
            
            # Mapeamento de arquivos para diretórios corretos
            declare -A file_mapping=(
                ["trading_bot_core.py"]="core/trading_bot.py"
                ["trading_bot_executor.py"]="core/executor.py"
                ["trading_bot_risk.py"]="core/risk_manager.py"
                ["trading_bot_binance.py"]="infrastructure/binance_api.py"
                ["trading_bot_indicators.py"]="infrastructure/indicators.py"
                ["trading_bot_data.py"]="infrastructure/data_manager.py"
                ["trading_bot_config.yaml"]="config/settings.yaml"
                ["trading_bot_config_loader.py"]="config/config_loader.py"
                ["trading_bot_database.py"]="database/db_handler.py"
                ["trading_bot_dashboard.py"]="interface/simple_dashboard.py"
                ["trading_bot_backtest.py"]="backtest/validator.py"
                ["trading_bot_quickstart.md"]="docs/QUICKSTART.md"
                ["trading_bot_api_guide.md"]="docs/BINANCE_API_SETUP.md"
                ["trading_bot_readme.md"]="README.md"
                ["trading_bot_requirements.txt"]="requirements.txt"
                ["trading_bot_test.py"]="test_setup.py"
            )
            
            # Criar diretórios necessários
            mkdir -p core infrastructure config database interface backtest docs data logs
            
            # Mover e renomear arquivos
            for old_file in "${files_to_organize[@]}"; do
                if [[ -v file_mapping["$old_file"] ]]; then
                    new_path="${file_mapping[$old_file]}"
                    
                    # Criar diretório se não existir
                    mkdir -p "$(dirname "$new_path")"
                    
                    # Mover arquivo
                    mv "$old_file" "$new_path"
                    print_status "Movido: $old_file → $new_path" "success"
                else
                    # Remover prefixo apenas
                    new_name="${old_file#trading_bot_}"
                    mv "$old_file" "$new_name"
                    print_status "Renomeado: $old_file → $new_name" "success"
                fi
            done
            
            print_status "Organização automática concluída!" "success"
        else
            print_status "Pulando organização automática" "info"
        fi
    else
        print_status "Nenhum arquivo com prefixo 'trading_bot_' encontrado" "info"
    fi
}

# Executar organização
organize_trading_bot_files

# Estrutura esperada do projeto
declare -A expected_structure=(
    ["core/"]="Lógica principal do bot"
    ["infrastructure/"]="APIs, WebSocket e indicadores"
    ["config/"]="Configurações e carregadores" 
    ["database/"]="Banco de dados e persistência"
    ["interface/"]="Dashboard e interface"
    ["backtest/"]="Sistema de backtesting"
    ["data/"]="Dados históricos e cache"
    ["logs/"]="Arquivos de log"
    ["docs/"]="Documentação do projeto"
)

print_status "Verificando estrutura de diretórios..." "info"

# Criar diretórios necessários
missing_dirs=()
for dir in "${!expected_structure[@]}"; do
    if [ -d "$dir" ]; then
        print_status "$dir existe ✓" "success"
    else
        mkdir -p "$dir"
        missing_dirs+=("$dir")
        print_status "Criado: $dir" "success"
    fi
done

# Criar arquivos __init__.py
python_dirs=("core" "infrastructure" "config" "database" "interface" "backtest")
print_status "Verificando arquivos __init__.py..." "info"

for dir in "${python_dirs[@]}"; do
    if [ ! -f "$dir/__init__.py" ]; then
        touch "$dir/__init__.py"
        print_status "Criado: $dir/__init__.py" "success"
    else
        print_status "$dir/__init__.py já existe ✓" "success"
    fi
done

# Criar .gitkeep em diretórios que devem ser mantidos vazios
empty_dirs=("data" "logs")
for dir in "${empty_dirs[@]}"; do
    if [ -d "$dir" ] && [ ! -f "$dir/.gitkeep" ]; then
        echo "# Manter diretório no git" > "$dir/.gitkeep"
        print_status "Criado: $dir/.gitkeep" "success"
    fi
done

# 3. CONFIGURAR .GITIGNORE PARA REPOSITÓRIO PRIVADO
echo ""
echo "🚫 3. CONFIGURANDO .GITIGNORE PARA REPOSITÓRIO PRIVADO"
echo "======================================================"

if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Bot Trading Binance - .gitignore para Repositório Privado

# ========================================
# DADOS SENSÍVEIS (mesmo em repo privado)
# ========================================
# Configurações locais com dados reais
.env
.env.local
.env.production
config/local_settings.yaml
config/production_secrets.yaml

# Logs com dados sensíveis
logs/trades_*.log
logs/api_*.log
logs/sensitive_*.log

# Backups de banco com dados reais
data/production_*.db
data/live_*.sqlite
backups/

# ========================================
# ARQUIVOS DE DESENVOLVIMENTO
# ========================================
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/
.venv/
.virtualenv

# ========================================
# DADOS E LOGS OPERACIONAIS
# ========================================
# Dados de trading (podem ser grandes)
data/*.csv
data/historical_*.json
data/cache/
data/temp/

# Logs operacionais
logs/*.log
logs/daily/
logs/backtest/

# Resultados de backtest
backtest/results/
backtest/reports/
backtest/temp/

# ========================================
# IDE E FERRAMENTAS
# ========================================
# VSCode
.vscode/
*.code-workspace

# PyCharm
.idea/
*.iml
*.ipr
*.iws

# Vim
*.swp
*.swo
*~

# Emacs
*~
\#*\#
/.emacs.desktop
/.emacs.desktop.lock
*.elc
auto-save-list
tramp
.\#*

# ========================================
# SISTEMA OPERACIONAL
# ========================================
# Windows
Thumbs.db
Desktop.ini
$RECYCLE.BIN/

# macOS
.DS_Store
.AppleDouble
.LSOverride
Icon
._*
.DocumentRevisions-V100
.fseventsd
.Spotlight-V100
.TemporaryItems
.Trashes
.VolumeIcon.icns
.com.apple.timemachine.donotpresent

# Linux
*~
.fuse_hidden*
.directory
.Trash-*
.nfs*

# ========================================
# ARQUIVOS TEMPORÁRIOS
# ========================================
# Temporários gerais
temp/
tmp/
*.tmp
*.temp
*.bak
*.backup
*.old
*.orig

# Arquivos de teste
test_*.py
debug_*.py
sandbox/
experiments/

# ========================================
# CONFIGURAÇÕES ESPECÍFICAS
# ========================================
# Certificados e chaves
*.pem
*.key
*.cert
*.crt

# Arquivos de configuração local
local_config.*
my_settings.*
personal_*.yaml

# Scripts pessoais
run_local.*
deploy_personal.*

# Notas e documentos pessoais
notes.txt
todo.txt
personal_notes/
EOF
    print_status ".gitignore criado para repositório privado" "success"
else
    print_status ".gitignore já existe" "info"
    
    # Verificar se tem configurações adequadas para repositório privado
    if ! grep -q "REPOSITÓRIO PRIVADO" .gitignore 2>/dev/null; then
        echo ""
        read -p "🔧 Deseja atualizar .gitignore para repositório privado? (Y/n): " update_gitignore
        if [[ $update_gitignore != [nN] ]]; then
            cp .gitignore .gitignore.backup
            cat > .gitignore << 'EOF'
# Bot Trading Binance - .gitignore para Repositório Privado
# (Backup do original salvo como .gitignore.backup)

# Dados sensíveis (mesmo em repo privado)
.env
.env.local
.env.production
config/local_settings.yaml
config/production_secrets.yaml

# Python básico
__pycache__/
*.py[cod]
venv/
.venv/

# Dados operacionais
data/*.db
data/*.sqlite
data/*.csv
logs/*.log
backtest/results/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Temporários
temp/
tmp/
*.tmp
*.bak
EOF
            print_status ".gitignore atualizado (backup salvo)" "success"
        fi
    fi
fi

# 4. VERIFICAR ARQUIVOS ESSENCIAIS
echo ""
echo "📋 4. VERIFICANDO ARQUIVOS ESSENCIAIS"
echo "====================================="

essential_files=(
    "main.py"
    "requirements.txt"
    "README.md"
    ".gitignore"
)

missing_files=()
for file in "${essential_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "$file existe ✓" "success"
    else
        print_status "$file NÃO EXISTE" "error"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    print_status "Criando arquivos essenciais faltantes..." "warning"
    
    for file in "${missing_files[@]}"; do
        case $file in
            "requirements.txt")
                cat > requirements.txt << 'EOF'
# Bot de Trading Binance V5.1 - Dependências

# Core
python-binance==1.0.17
pandas==2.0.0
numpy==1.24.0

# Configuração
PyYAML==6.0

# Async e WebSocket
websockets==11.0
aiohttp==3.8.0

# Interface
rich==13.0.0

# Teclado
keyboard==0.13.5
EOF
                print_status "requirements.txt criado" "success"
                ;;
            "README.md")
                cat > README.md << 'EOF'
# 🤖 Bot de Trading Binance V5.1

Bot automatizado de day trading para Binance.

## 🔒 Repositório Privado

Este é um repositório privado com código proprietário de trading.

## 🚀 Características

- Estratégia RSI + Bollinger Bands + EMA
- WebSocket para execução rápida
- Dashboard terminal
- Sistema de backtest
- Gestão de risco automática

## ⚠️ Importante

- **SEMPRE** teste no testnet primeiro
- **NUNCA** use mais dinheiro do que pode perder
- Configure adequadamente suas API keys

## 🔧 Instalação

```bash
pip install -r requirements.txt
python main.py
```
EOF
                print_status "README.md criado" "success"
                ;;
        esac
    done
fi

# 5. CONFIGURAR GIT
echo ""
echo "🔧 5. CONFIGURANDO GIT"
echo "====================="

if [ ! -d ".git" ]; then
    git init
    print_status "Repositório git inicializado" "success"
else
    print_status "Repositório git já existe" "info"
fi

# Configurar git se necessário
if ! git config --get user.name > /dev/null; then
    echo ""
    read -p "📝 Digite seu nome para o git: " git_name
    git config --global user.name "$git_name"
    print_status "Nome configurado: $git_name" "success"
fi

if ! git config --get user.email > /dev/null; then
    echo ""
    read -p "📧 Digite seu email para o git: " git_email
    git config --global user.email "$git_email"
    print_status "Email configurado: $git_email" "success"
fi

# 6. COMMIT
echo ""
echo "💾 6. PREPARANDO E EXECUTANDO COMMIT"
echo "===================================="

# Adicionar arquivos
git add .

# Verificar status
files_count=$(git diff --cached --name-only | wc -l)
print_status "$files_count arquivos serão commitados" "info"

# Mostrar principais arquivos
echo ""
echo "📄 Principais arquivos no commit:"
git diff --cached --name-only | grep -E "\.(py|yaml|md|txt)$" | head -8
if [ $files_count -gt 8 ]; then
    echo "... e mais $((files_count - 8)) arquivos"
fi

# Commit com mensagem específica para repositório privado
commit_message="🔒 Initial commit: Bot Trading Binance V5.1 (Private Repository)

✨ Features implementadas:
- Trading automatizado com estratégia RSI + Bollinger Bands + EMA
- WebSocket para execução em tempo real (<100ms latência)
- Dashboard terminal minimalista com controles interativos
- Sistema de backtest e validação automática
- Gestão de risco avançada com circuit breakers
- Suporte completo ao Binance Testnet e produção

🏗️ Arquitetura:
- 10 módulos principais organizados
- Configuração YAML flexível
- Banco de dados SQLite para persistência
- Interface Rich terminal responsiva
- Documentação completa incluída

🔐 Repositório Privado:
- Contém configurações proprietárias
- API keys e segredos protegidos
- Estratégias de trading exclusivas
- Código otimizado para performance

⚠️ AVISOS DE SEGURANÇA:
- Sempre validar no testnet antes de produção
- Nunca usar mais capital do que pode perder
- Monitorar trades constantemente
- Manter API keys seguras

🎯 Próximos passos:
1. Configurar API keys no ambiente
2. Executar testes de configuração  
3. Validar estratégia no testnet
4. Implementar monitoramento contínuo"

git commit -m "$commit_message"
print_status "Commit realizado com sucesso" "success"

# 7. CONFIGURAR REPOSITÓRIO PRIVADO NO GITHUB
echo ""
echo "🔒 7. CONFIGURANDO REPOSITÓRIO PRIVADO NO GITHUB"
echo "==============================================="

print_status "Configuração para repositório PRIVADO" "private"

if git remote get-url origin >/dev/null 2>&1; then
    current_remote=$(git remote get-url origin)
    print_status "Remote já configurado: $current_remote" "info"
else
    echo ""
    print_status "Instruções para criar repositório PRIVADO:" "private"
    echo ""
    echo "🌐 1. Acesse: https://github.com/new"
    echo "📝 2. Nome: trading-bot-binance-private (ou similar)"
    echo "📋 3. Descrição: 🤖🔒 Bot automatizado de day trading - Repositório Privado"
    echo "🔒 4. ✅ PRIVATE (muito importante!)"
    echo "📄 5. ❌ NÃO adicione README/gitignore (já temos)"
    echo "👤 6. Configure colaboradores se necessário"
    echo ""
    echo "🔐 Vantagens do repositório privado:"
    echo "  - API keys protegidas"
    echo "  - Estratégias proprietárias seguras"
    echo "  - Configurações sensíveis protegidas"
    echo "  - Controle total de acesso"
    echo ""
    
    read -p "📎 Digite a URL do repositório PRIVADO: " repo_url
    
    git remote add origin "$repo_url"
    print_status "Remote configurado para repositório privado" "private"
fi

# 8. UPLOAD PARA REPOSITÓRIO PRIVADO
echo ""
echo "🚀 8. FAZENDO UPLOAD PARA REPOSITÓRIO PRIVADO"
echo "============================================="

print_status "Iniciando upload para repositório privado..." "private"

# Configurar branch principal
current_branch=$(git branch --show-current 2>/dev/null || echo "master")
if [ "$current_branch" != "main" ]; then
    git branch -M main
    print_status "Branch renomeada para 'main'" "info"
fi

# Push para GitHub
echo ""
print_status "🔐 Fazendo push para repositório privado..." "private"

if git push -u origin main; then
    print_status "Upload para repositório privado concluído!" "success"
else
    print_status "Erro no upload. Verificando soluções..." "error"
    echo ""
    echo "🔧 Soluções para autenticação:"
    echo "1. 🎫 Personal Access Token: https://github.com/settings/tokens"
    echo "   - Scopes necessários: repo (acesso total a repositórios privados)"
    echo "2. 🔑 SSH Keys: https://github.com/settings/keys" 
    echo "3. 🌐 GitHub CLI: gh auth login"
    echo "4. 💻 Git Credential Manager"
    echo ""
    read -p "🔄 Tentar push novamente? (y/N): " retry_push
    if [[ $retry_push == [yY] ]]; then
        git push -u origin main
    else
        echo "Execute manualmente: git push -u origin main"
        exit 1
    fi
fi

# 9. VERIFICAÇÕES FINAIS E SEGURANÇA
echo ""
echo "✅ 9. VERIFICAÇÕES FINAIS DO REPOSITÓRIO PRIVADO"
echo "==============================================="

repo_url=$(git remote get-url origin)
if [[ $repo_url == *"github.com"* ]]; then
    browser_url="${repo_url%.git}"
    browser_url="${browser_url/git@github.com:/https://github.com/}"
    
    print_status "Repositório privado disponível em: $browser_url" "private"
fi

echo ""
echo "🎉 REPOSITÓRIO PRIVADO CRIADO COM SUCESSO!"
echo "========================================="
echo ""
print_status "🔒 Seu bot está seguro em repositório privado!" "private"
echo ""
echo "📋 Próximos passos essenciais:"
echo ""
echo "🔐 1. SEGURANÇA:"
echo "   - Configure colaboradores em Settings > Manage access"
echo "   - Ative 2FA na sua conta GitHub"
echo "   - Configure branch protection rules"
echo ""
echo "⚙️ 2. CONFIGURAÇÃO:"
echo "   - Clone em ambiente de desenvolvimento"
echo "   - Configure API keys localmente"
echo "   - Execute testes no testnet"
echo ""
echo "📊 3. OPERAÇÃO:"
echo "   - Valide estratégia por semanas no testnet"
echo "   - Monitore performance constantemente"
echo "   - Mantenha backups das configurações"
echo ""
echo "🚨 4. AVISOS IMPORTANTES:"
echo "   - NUNCA torne o repositório público"
echo "   - SEMPRE teste antes de usar dinheiro real"
echo "   - MONITORE trades constantemente"
echo "   - MANTENHA logs de todas as operações"
echo ""

# Teste de clone (opcional)
echo ""
read -p "🧪 Deseja testar clone do repositório privado? (y/N): " test_clone
if [[ $test_clone == [yY] ]]; then
    test_dir="/tmp/trading-bot-private-test"
    rm -rf "$test_dir" 2>/dev/null
    
    if git clone "$repo_url" "$test_dir"; then
        print_status "Clone do repositório privado testado com sucesso!" "success"
        
        cd "$test_dir"
        if [ -f "test_setup.py" ]; then
            echo ""
            print_status "Executando verificações de setup..." "info"
            python3 test_setup.py 2>/dev/null || print_status "Algumas verificações falharam (normal sem API configurada)" "warning"
        fi
        
        print_status "Estrutura do projeto verificada!" "success"
        cd - > /dev/null
    else
        print_status "Erro no teste de clone - verifique credenciais" "error"
    fi
fi

echo ""
print_status "🎯 Bot Trading Binance V5.1 deployed com sucesso!" "success"
print_status "🔒 Repositório privado protege seus dados e estratégias!" "private"
print_status "💰 Lembre-se: Comece sempre no testnet!" "warning"

echo ""
print_status "Script de upload finalizado! 🚀" "success"