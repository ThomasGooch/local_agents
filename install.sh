#!/bin/bash

# Local Agents Installation Script
# This script installs the Local Agents suite globally using Poetry on macOS/Linux

set -e  # Exit on any error

INSTALL_DIR="$HOME/.local/bin"
PROJECT_DIR="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
check_project_directory() {
    if [[ ! -f "pyproject.toml" ]] || [[ ! -d "src/local_agents" ]]; then
        print_error "This script must be run from the local-agents project root directory"
        print_info "Please navigate to the directory containing pyproject.toml and try again"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check Python version (3.9-3.12 recommended)
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9-3.12."
        print_info "Recommended: Use pyenv to install Python 3.11.9"
        exit 1
    fi
    
    # Use python or python3, whichever is available
    PYTHON_CMD="python3"
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "Found Python $PYTHON_VERSION using command: $PYTHON_CMD"
    
    # Warn if using Python 3.13+ (compatibility issues)
    if $PYTHON_CMD -c 'import sys; exit(0 if sys.version_info[:2] <= (3, 12) else 1)' 2>/dev/null; then
        print_success "Python version is compatible (3.9-3.12 recommended)"
    else
        print_warning "Python $PYTHON_VERSION detected. Versions 3.9-3.12 are recommended for best compatibility."
        print_info "Consider using pyenv to install Python 3.11.9: pyenv install 3.11.9 && pyenv local 3.11.9"
    fi
    
    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed. Please install Poetry first:"
        echo "  curl -sSL https://install.python-poetry.org | python3 -"
        echo "  # or: pip install poetry"
        echo "  # or: brew install poetry (macOS)"
        exit 1
    fi
    
    print_success "Poetry is installed"
    
    # Check Ollama
    if ! command -v ollama &> /dev/null; then
        print_warning "Ollama is not installed. You can install it with:"
        echo "  brew install ollama  # macOS"
        echo "  # or download from https://ollama.ai"
        print_info "Continuing installation, but you'll need Ollama to run the agents"
    else
        print_success "Ollama is installed"
    fi
    
    # Check if Ollama is running
    if command -v ollama &> /dev/null; then
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_success "Ollama server is running"
        else
            print_warning "Ollama is installed but not running. Start it with: ollama serve"
        fi
    fi
}

# Create installation directory
create_install_dir() {
    print_info "Creating installation directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    
    # Add to PATH if not already present
    SHELL_RC=""
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
    elif [[ "$SHELL" == *"bash"* ]]; then
        SHELL_RC="$HOME/.bashrc"
    fi
    
    if [[ -n "$SHELL_RC" ]]; then
        if ! grep -q "$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
            print_success "Added $INSTALL_DIR to PATH in $SHELL_RC"
            print_warning "Please run: source $SHELL_RC (or restart your terminal)"
        fi
    fi
}

# Install using Poetry
install_with_poetry() {
    print_info "Installing Local Agents using Poetry..."
    
    # Install dependencies
    print_info "Installing dependencies with Poetry..."
    poetry install
    
    # Build the package
    print_info "Building package..."
    poetry build
    
    print_success "Package installed successfully with Poetry"
}

# Create wrapper scripts
create_wrapper_scripts() {
    print_info "Creating command-line scripts..."
    
    # Get Poetry project directory for consistent execution
    POETRY_PROJECT_DIR="$PROJECT_DIR"
    
    # Main lagents command
    cat > "$INSTALL_DIR/lagents" << EOF
#!/bin/bash
cd "$POETRY_PROJECT_DIR"
exec poetry run python -m local_agents.cli "\$@"
EOF
    chmod +x "$INSTALL_DIR/lagents"
    
    # Individual command shortcuts
    cat > "$INSTALL_DIR/la-plan" << EOF
#!/bin/bash
cd "$POETRY_PROJECT_DIR"
exec poetry run python -m local_agents.cli plan "\$@"
EOF
    chmod +x "$INSTALL_DIR/la-plan"
    
    cat > "$INSTALL_DIR/la-code" << EOF
#!/bin/bash
cd "$POETRY_PROJECT_DIR"
exec poetry run python -m local_agents.cli code "\$@"
EOF
    chmod +x "$INSTALL_DIR/la-code"
    
    cat > "$INSTALL_DIR/la-test" << EOF
#!/bin/bash
cd "$POETRY_PROJECT_DIR"
exec poetry run python -m local_agents.cli test "\$@"
EOF
    chmod +x "$INSTALL_DIR/la-test"
    
    cat > "$INSTALL_DIR/la-review" << EOF
#!/bin/bash
cd "$POETRY_PROJECT_DIR"
exec poetry run python -m local_agents.cli review "\$@"
EOF
    chmod +x "$INSTALL_DIR/la-review"
    
    cat > "$INSTALL_DIR/la-workflow" << EOF
#!/bin/bash
cd "$POETRY_PROJECT_DIR"
exec poetry run python -m local_agents.cli workflow "\$@"
EOF
    chmod +x "$INSTALL_DIR/la-workflow"
    
    print_success "Created command-line scripts using Poetry"
}

# Pull recommended models
pull_models() {
    if command -v ollama &> /dev/null && curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_info "Pulling recommended models (this may take a while)..."
        
        models=("llama3.1:8b" "codellama:7b" "deepseek-coder:6.7b")
        
        for model in "${models[@]}"; do
            print_info "Pulling $model..."
            if ollama pull "$model"; then
                print_success "Successfully pulled $model"
            else
                print_warning "Failed to pull $model - you can try manually later with: ollama pull $model"
            fi
        done
    else
        print_warning "Skipping model download - Ollama not available"
        print_info "After installing and starting Ollama, you can pull models with:"
        echo "  ollama pull llama3.1:8b"
        echo "  ollama pull codellama:7b"
        echo "  ollama pull deepseek-coder:6.7b"
    fi
}

# Test installation
test_installation() {
    print_info "Testing installation..."
    
    # Test if commands are accessible
    if "$INSTALL_DIR/lagents" --version &> /dev/null; then
        print_success "lagents command works"
    else
        print_error "lagents command failed"
        return 1
    fi
    
    # Test configuration creation
    if "$INSTALL_DIR/lagents" config --show &> /dev/null; then
        print_success "Configuration system works"
    else
        print_warning "Configuration test failed - this might be normal on first run"
    fi
}

# Create uninstall script
create_uninstall_script() {
    print_info "Creating uninstall script..."
    
    cat > "$INSTALL_DIR/uninstall-lagents" << 'EOF'
#!/bin/bash

INSTALL_DIR="$HOME/.local/bin"
CONFIG_FILE="$HOME/.local_agents_config.yml"

echo "Uninstalling Local Agents (Poetry Version)..."

# Remove scripts
rm -f "$INSTALL_DIR/lagents"
rm -f "$INSTALL_DIR/la-plan"
rm -f "$INSTALL_DIR/la-code"
rm -f "$INSTALL_DIR/la-test"
rm -f "$INSTALL_DIR/la-review"
rm -f "$INSTALL_DIR/la-workflow"
rm -f "$INSTALL_DIR/uninstall-lagents"
echo "Removed command-line scripts"

# Note about Poetry environment
echo "Note: Poetry virtual environment is managed by Poetry itself"
echo "To completely remove the Poetry environment, run:"
echo "  cd [project-directory] && poetry env remove --all"

# Ask about config file
if [[ -f "$CONFIG_FILE" ]]; then
    read -p "Remove configuration file? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$CONFIG_FILE"
        echo "Removed configuration file"
    fi
fi

echo "Local Agents uninstalled successfully"
echo "You may need to remove $INSTALL_DIR from your PATH manually"
EOF
    
    chmod +x "$INSTALL_DIR/uninstall-lagents"
    print_success "Created uninstall script: $INSTALL_DIR/uninstall-lagents"
}

# Main installation function
main() {
    print_info "Local Agents Installation Script (Poetry Version)"
    print_info "================================================="
    
    check_project_directory
    check_dependencies
    create_install_dir
    install_with_poetry
    create_wrapper_scripts
    pull_models
    
    if test_installation; then
        create_uninstall_script
        
        print_success "Installation completed successfully using Poetry!"
        echo
        print_info "Available commands:"
        echo "  lagents          - Main CLI interface"
        echo "  la-plan          - Planning agent"
        echo "  la-code          - Coding agent"
        echo "  la-test          - Testing agent"
        echo "  la-review        - Review agent"
        echo "  la-workflow      - Workflow execution"
        echo
        print_info "Examples:"
        echo "  lagents plan 'Add user authentication'"
        echo "  la-code 'Create a REST API endpoint'"
        echo "  la-workflow feature-dev 'Add dark mode'"
        echo
        print_info "Development commands:"
        echo "  poetry run pytest              - Run tests"
        echo "  poetry run python run_tests.py - Advanced test runner"
        echo
        print_info "Configuration:"
        echo "  lagents config --show"
        echo "  Configuration file: ~/.local_agents_config.yml"
        echo
        print_info "Python version: $PYTHON_VERSION (recommended: 3.9-3.12)"
        print_info "To uninstall: $INSTALL_DIR/uninstall-lagents"
        
        if [[ -n "$SHELL_RC" ]]; then
            print_warning "Don't forget to restart your terminal or run: source $SHELL_RC"
        fi
    else
        print_error "Installation test failed!"
        exit 1
    fi
}

# Run main function
main "$@"