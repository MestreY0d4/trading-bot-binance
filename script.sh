#!/bin/bash
# Script automatizado para upload do Bot Trading para GitHub
# Versão melhorada com verificação de segurança mais precisa

set -e  # Parar se qualquer comando falhar

echo "🚀 BOT TRADING BINANCE - UPLOAD PARA GITHUB"
echo "============================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para print colorido
print_status() {
    case $2 in
        "error") echo -e "${RED}❌ $1${NC}" ;;
        "success") echo -e "${GREEN}✅ $1${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️ $1${NC}" ;;
        "info") echo -e "${BLUE}ℹ️ $1${NC}" ;;
        *) echo "$1" ;;
    esac
}

# Verificar se estamos no diretório correto
if [ ! -f "main.py" ]; then
    print_status "Erro: main.py não encontrado. Execute no diretório do projeto!" "error"
    exit 1
fi

print_status "Verificando projeto..." "info"

# 1. VERIFICAÇÕES DE SEGURANÇA MELHORADAS
echo ""
echo "🔐 1. VERIFICAÇÕES DE SEGURANÇA"
echo "================================"

# Função para verificar API keys mais precisa
check_api_keys() {
    local found_issues=false
    
    # Padrões específicos para diferentes tipos de API keys
    local patterns=(
        # Binance API keys (começam com caracteres específicos)
        "api_key.*=.*['\"][A-Za-z0-9]{64}['\"]"
        "secret.*=.*['\"][A-Za-z0-9/+=]{64}['\"]"
        "API_KEY.*=.*['\"][A-Za-z0-9]{64}['\"]"
        "SECRET.*=.*['\"][A-Za-z0-9/+=]{64}['\"]"
        
        # Tokens diversos
        "token.*=.*['\"][A-Za-z0-9_-]{20,}['\"]"
        "TOKEN.*=.*['\"][A-Za-z0-9_-]{20,}['\"]"
        
        # Padrões suspeitos específicos
        "['\"][A-Za-z0-9]{50,}['\"].*#.*[Kk]ey"
        "['\"][A-Za-z0-9/+=]{50,}['\"].*#.*[Ss]ecret"
    )
    
    for pattern in "${patterns[@]}"; do
        if grep -r -E "$pattern" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=__pycache__ --exclude="*.log" --exclude="*.db" 2>/dev/null; then
            print_status "PERIGO: Possível API key encontrada!" "error"
            echo "Padrão detectado: $pattern"
            found_issues=true
        fi
    done
    
    return $found_issues
}

# Verificar palavras suspeitas que indicam produção
check_production_config() {
    local suspicious_terms=(
        "YOUR_REAL_API_KEY"
        "YOUR_REAL_SECRET"
        "PRODUCTION_API"
        "LIVE_TRADING.*true"
        "testnet.*false"
        "sandbox.*false"
    )
    
    for term in "${suspicious_terms[@]}"; do
        if grep -r -i -E "$term" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=__pycache__ 2>/dev/null; then
            print_status "PERIGO: Configuração de produção encontrada!" "error"
            echo "Termo suspeito: $term"
            return 1
        fi
    done
    return 0
}

# Executar verificações
print_status "Verificando API keys hardcoded..." "info"
if ! check_api_keys; then
    echo ""
    print_status "❌ VERIFICAÇÃO DE SEGURANÇA FALHOU" "error"
    echo ""
    echo "Soluções:"
    echo "1. Mova API keys para arquivo .env"
    echo "2. Use variáveis de ambiente"
    echo "3. Configure arquivo config.yaml separado"
    echo "4. Adicione arquivos sensíveis ao .gitignore"
    echo ""
    read -p "Mostrar arquivos com possíveis problemas? (y/N): " show_files
    if [[ $show_files == [yY] ]]; then
        echo ""
        echo "Arquivos que podem conter API keys:"
        grep -r -l -E "(api_key|secret|token)" . --exclude-dir=.git --exclude-dir=venv 2>/dev/null || echo "Nenhum arquivo específico identificado"
    fi
    echo ""
    read -p "Continuar mesmo assim? (y/N): " force_continue
    if [[ $force_continue != [yY] ]]; then
        exit 1
    fi
    print_status "CONTINUANDO COM RISCO (conforme solicitado)" "warning"
else
    print_status "Nenhuma API key hardcoded encontrada" "success"
fi

print_status "Verificando configurações de produção..." "info"
if ! check_production_config; then
    echo ""
    read -p "Continuar mesmo assim? (y/N): " force_continue
    if [[ $force_continue != [yY] ]]; then
        exit 1
    fi
    print_status "CONTINUANDO COM RISCO (conforme solicitado)" "warning"
else
    print_status "Nenhuma configuração de produção perigosa encontrada" "success"
fi

# 2. VERIFICAR E ORGANIZAR ESTRUTURA
echo ""
echo "📁 2. VERIFICANDO E ORGANIZANDO ESTRUTURA"
echo "========================================="

# Estrutura desejada do projeto
declare -A expected_structure=(
    ["core/"]="Módulos principais do bot"
    ["infrastructure/"]="Conexões e WebSocket"
    ["config/"]="Arquivos de configuração" 
    ["database/"]="Modelos e conexão DB"
    ["interface/"]="Dashboard e UI"
    ["backtest/"]="Sistema de backtesting"
    ["data/"]="Dados e históricos"
    ["logs/"]="Arquivos de log"
    ["docs/"]="Documentação"
)

# Arquivos que devem estar em cada diretório (exemplos)
declare -A expected_files=(
    ["core/trading_bot.py"]="core/"
    ["core/strategy.py"]="core/"
    ["core/risk_manager.py"]="core/"
    ["infrastructure/binance_client.py"]="infrastructure/"
    ["infrastructure/websocket_handler.py"]="infrastructure/"
    ["config/config.yaml"]="config/"
    ["config/settings.py"]="config/"
    ["database/models.py"]="database/"
    ["database/database.py"]="database/"
    ["interface/dashboard.py"]="interface/"
    ["interface/terminal_ui.py"]="interface/"
    ["backtest/backtester.py"]="backtest/"
    ["backtest/validator.py"]="backtest/"
)

print_status "Verificando estrutura atual..." "info"

# Função para verificar e criar diretórios
check_and_create_dirs() {
    local missing_dirs=()
    local existing_dirs=()
    
    for dir in "${!expected_structure[@]}"; do
        if [ -d "$dir" ]; then
            existing_dirs+=("$dir")
            print_status "$dir existe ✓" "success"
        else
            missing_dirs+=("$dir")
            print_status "$dir NÃO EXISTE" "warning"
        fi
    done
    
    if [ ${#missing_dirs[@]} -gt 0 ]; then
        echo ""
        print_status "Criando diretórios faltantes..." "info"
        for dir in "${missing_dirs[@]}"; do
            mkdir -p "$dir"
            print_status "Criado: $dir" "success"
        done
    fi
    
    echo ""
    print_status "${#existing_dirs[@]} diretórios já existiam, ${#missing_dirs[@]} foram criados" "info"
}

# Função para verificar __init__.py
check_and_create_init_files() {
    local python_dirs=("core" "infrastructure" "config" "database" "interface" "backtest")
    local missing_init=()
    local existing_init=()
    
    print_status "Verificando arquivos __init__.py..." "info"
    
    for dir in "${python_dirs[@]}"; do
        if [ -f "$dir/__init__.py" ]; then
            existing_init+=("$dir/__init__.py")
            print_status "$dir/__init__.py existe ✓" "success"
        else
            missing_init+=("$dir/__init__.py")
            print_status "$dir/__init__.py NÃO EXISTE" "warning"
        fi
    done
    
    if [ ${#missing_init[@]} -gt 0 ]; then
        echo ""
        print_status "Criando arquivos __init__.py faltantes..." "info"
        for init_file in "${missing_init[@]}"; do
            touch "$init_file"
            print_status "Criado: $init_file" "success"
        done
    fi
    
    echo ""
    print_status "${#existing_init[@]} __init__.py já existiam, ${#missing_init[@]} foram criados" "info"
}

# Função para verificar posicionamento de arquivos
check_file_positioning() {
    print_status "Verificando posicionamento de arquivos..." "info"
    
    local misplaced_files=()
    local correctly_placed=()
    local suggestions=()
    
    # Verificar se arquivos estão nos diretórios corretos
    for file_path in "${!expected_files[@]}"; do
        expected_dir="${expected_files[$file_path]}"
        
        # Procurar o arquivo em qualquer lugar
        if [ -f "$file_path" ]; then
            correctly_placed+=("$file_path")
            print_status "$file_path está no lugar correto ✓" "success"
        else
            # Procurar arquivo com mesmo nome em outros lugares
            filename=$(basename "$file_path")
            found_files=$(find . -name "$filename" -type f 2>/dev/null | grep -v __pycache__ | head -5)
            
            if [ ! -z "$found_files" ]; then
                misplaced_files+=("$filename")
                print_status "$filename encontrado em lugar errado" "warning"
                
                while IFS= read -r found_file; do
                    suggestions+=("mv '$found_file' '$file_path'")
                    echo "  Encontrado em: $found_file"
                    echo "  Deveria estar em: $file_path"
                done <<< "$found_files"
            fi
        fi
    done
    
    # Mostrar sugestões de reorganização
    if [ ${#suggestions[@]} -gt 0 ]; then
        echo ""
        print_status "Sugestões de reorganização encontradas!" "warning"
        echo ""
        read -p "Deseja que eu reorganize os arquivos automaticamente? (y/N): " auto_reorganize
        
        if [[ $auto_reorganize == [yY] ]]; then
            print_status "Reorganizando arquivos..." "info"
            for suggestion in "${suggestions[@]}"; do
                echo "Executando: $suggestion"
                eval "$suggestion" 2>/dev/null || print_status "Erro ao mover arquivo" "warning"
            done
            print_status "Reorganização concluída!" "success"
        else
            echo "Para reorganizar manualmente, execute:"
            for suggestion in "${suggestions[@]}"; do
                echo "  $suggestion"
            done
        fi
    fi
    
    echo ""
    print_status "${#correctly_placed[@]} arquivos no lugar correto, ${#misplaced_files[@]} precisam ser movidos" "info"
}

# Função para criar .gitkeep em diretórios vazios
create_gitkeep_files() {
    local empty_dirs=("data" "logs")
    
    print_status "Verificando .gitkeep em diretórios vazios..." "info"
    
    for dir in "${empty_dirs[@]}"; do
        if [ -d "$dir" ] && [ -z "$(ls -A $dir 2>/dev/null)" ]; then
            if [ ! -f "$dir/.gitkeep" ]; then
                echo "# Manter diretório no git" > "$dir/.gitkeep"
                print_status "Criado $dir/.gitkeep" "success"
            else
                print_status "$dir/.gitkeep já existe ✓" "success"
            fi
        elif [ -d "$dir" ] && [ ! -z "$(ls -A $dir 2>/dev/null)" ]; then
            print_status "$dir não está vazio (não precisa de .gitkeep)" "info"
        fi
    done
}

# Executar todas as verificações
check_and_create_dirs
echo ""
check_and_create_init_files
echo ""
check_file_positioning
echo ""
create_gitkeep_files

echo ""
print_status "Verificação de estrutura concluída!" "success"

# 3. VERIFICAR/CRIAR .GITIGNORE
echo ""
echo "🚫 3. CONFIGURANDO .GITIGNORE"
echo "============================="

if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# API Keys e Configurações Sensíveis
.env
.env.local
.env.production
config/secrets.yaml
config/production.yaml
api_keys.txt
secrets.txt

# Arquivos de dados
*.db
*.sqlite
*.sqlite3
data/*.csv
data/*.json
logs/*.log
backtest/results/*

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

# Virtual Environment
venv/
env/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporários
temp/
tmp/
*.tmp
*.bak
EOF
    print_status ".gitignore criado" "success"
else
    print_status ".gitignore já existe" "info"
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
        print_status "$file existe" "success"
    else
        print_status "$file NÃO EXISTE" "error"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    print_status "Arquivos essenciais faltando. Crie-os antes de continuar." "error"
    echo ""
    echo "Para criar arquivos em falta:"
    for file in "${missing_files[@]}"; do
        case $file in
            "requirements.txt")
                echo "echo 'requests\npandas\nnumpy\nbinance\npyyaml\nrich' > requirements.txt"
                ;;
            "README.md")
                echo "echo '# Bot Trading Binance' > README.md"
                ;;
        esac
    done
    exit 1
fi

# 5. INICIALIZAR GIT
echo ""
echo "🔧 5. CONFIGURANDO GIT"
echo "====================="

if [ ! -d ".git" ]; then
    git init
    print_status "Repositório git inicializado" "success"
else
    print_status "Repositório git já existe" "info"
fi

# Verificar configuração do git
if ! git config --get user.name > /dev/null; then
    echo ""
    read -p "Digite seu nome para o git: " git_name
    git config --global user.name "$git_name"
fi

if ! git config --get user.email > /dev/null; then
    echo ""
    read -p "Digite seu email para o git: " git_email
    git config --global user.email "$git_email"
fi

print_status "Configuração do git OK" "success"

# 6. ADICIONAR ARQUIVOS
echo ""
echo "📦 6. PREPARANDO COMMIT"
echo "======================"

# Adicionar todos os arquivos
git add .

# Verificar o que será commitado
files_count=$(git diff --cached --name-only | wc -l)
print_status "$files_count arquivos serão commitados" "info"

# Mostrar arquivos que serão commitados
echo ""
echo "Arquivos que serão commitados:"
git diff --cached --name-only | head -10
if [ $files_count -gt 10 ]; then
    echo "... e mais $((files_count - 10)) arquivos"
fi

# Verificar se há arquivos sensíveis sendo commitados
sensitive_files=$(git diff --cached --name-only | grep -E "\.(log|db|sqlite|env)$" || true)
if [ ! -z "$sensitive_files" ]; then
    print_status "ATENÇÃO: Arquivos sensíveis detectados no commit!" "warning"
    echo "$sensitive_files"
    read -p "Continuar mesmo assim? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        print_status "Removendo arquivos sensíveis do commit..." "info"
        echo "$sensitive_files" | xargs git reset HEAD
        git add .
    fi
fi

# 7. COMMIT
echo ""
echo "💾 7. FAZENDO COMMIT"
echo "==================="

commit_message="🎉 Initial commit: Bot Trading Binance V5.1

✨ Features:
- Estratégia RSI + Bollinger Bands + EMA  
- WebSocket para execução rápida
- Dashboard terminal minimalista
- Sistema de backtest e validação
- Gestão de risco com circuit breakers
- Suporte completo ao Binance Testnet

🔧 Estrutura:
- 10 módulos principais
- Configuração YAML
- Banco SQLite  
- Interface Rich terminal
- Documentação completa

⚠️ IMPORTANTE: Sempre teste no testnet antes de usar dinheiro real!"

git commit -m "$commit_message"
print_status "Commit realizado com sucesso" "success"

# 8. CONFIGURAR REMOTE
echo ""
echo "🌐 8. CONFIGURANDO GITHUB"
echo "========================="

if git remote get-url origin >/dev/null 2>&1; then
    current_remote=$(git remote get-url origin)
    print_status "Remote já configurado: $current_remote" "info"
else
    echo ""
    print_status "Configure o repositório GitHub primeiro:" "info"
    echo "1. Acesse: https://github.com/new"
    echo "2. Nome: trading-bot-binance"
    echo "3. Descrição: 🤖 Bot automatizado de day trading para Binance"
    echo "4. ✅ Public"
    echo "5. ❌ NÃO adicione README/gitignore (já temos)"
    echo ""
    read -p "Digite a URL do repositório (ex: https://github.com/user/repo.git): " repo_url
    
    git remote add origin "$repo_url"
    print_status "Remote configurado: $repo_url" "success"
fi

# 9. PUSH PARA GITHUB
echo ""
echo "🚀 9. FAZENDO UPLOAD"
echo "==================="

print_status "Fazendo push para GitHub..." "info"

# Renomear branch para main se necessário
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    git branch -M main
    print_status "Branch renomeada para 'main'" "info"
fi

# Fazer push
if git push -u origin main; then
    print_status "Upload concluído com sucesso!" "success"
else
    print_status "Erro no upload. Verifique suas credenciais." "error"
    echo ""
    echo "Soluções possíveis:"
    echo "1. Configure token do GitHub: https://github.com/settings/tokens"
    echo "2. Configure SSH keys: https://github.com/settings/keys"
    echo "3. Use: git push -u origin main (e digite credenciais)"
    exit 1
fi

# 10. VERIFICAÇÕES FINAIS
echo ""
echo "✅ 10. VERIFICAÇÕES FINAIS"
echo "=========================="

repo_url=$(git remote get-url origin)
if [[ $repo_url == *"github.com"* ]]; then
    # Extrair URL do browser
    browser_url="${repo_url%.git}"
    browser_url="${browser_url/git@github.com:/https://github.com/}"
    
    print_status "Repositório disponível em: $browser_url" "success"
fi

echo ""
echo "🎉 UPLOAD CONCLUÍDO COM SUCESSO!"
echo "================================="
echo ""
echo "Próximos passos:"
echo "1. Acesse seu repositório no GitHub"
echo "2. Verifique se o README.md está sendo exibido"
echo "3. Teste clone: git clone $repo_url"
echo "4. Adicione topics/tags no GitHub"
echo "5. Configure GitHub Actions (opcional)"
echo ""
print_status "Bot trading pronto para uso!" "success"
print_status "Lembre-se: SEMPRE teste no testnet primeiro!" "warning"

# Oferecer testar clone
echo ""
read -p "Deseja testar o clone em /tmp? (y/N): " test_clone
if [[ $test_clone == [yY] ]]; then
    cd /tmp
    rm -rf trading-bot-test 2>/dev/null
    if git clone "$repo_url" trading-bot-test; then
        print_status "Clone testado com sucesso!" "success"
        cd trading-bot-test
        if [ -f "test_setup.py" ]; then
            echo "Executando test_setup.py..."
            python test_setup.py || print_status "Alguns testes falharam (normal se API não configurada)" "warning"
        fi
    else
        print_status "Erro no teste de clone" "error"
    fi
fi

echo ""
print_status "Script finalizado! 🚀" "success"