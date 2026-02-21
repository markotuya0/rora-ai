#!/bin/bash

echo "🚀 Setting up Text-to-SQL AI Application..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check Ollama
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed"
    echo "📥 Pulling model..."
    ollama pull qwen2.5:0.5b
else
    echo "⚠️  Ollama not found. Install from https://ollama.ai"
fi

# Initialize database
echo "🗄️  Initializing database..."
python create_db.py

# Run tests
echo "🧪 Running tests..."
python test_utils.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Start API:       python api.py"
echo "  2. Start UI:        streamlit run app_v2.py"
echo "  3. Or use Docker:   docker-compose up"
echo ""
echo "Access points:"
echo "  - API:          http://localhost:8000"
echo "  - API Docs:     http://localhost:8000/docs"
echo "  - Streamlit UI: http://localhost:8501"
