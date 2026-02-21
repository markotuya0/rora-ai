# Contributing to Rora AI

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/rora-ai.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `make test`
6. Commit: `git commit -m "feat: your feature description"`
7. Push: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python create_db.py

# Run tests
make test
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Add docstrings to functions and classes
- Keep functions focused and modular
- Write meaningful commit messages

## Commit Message Format

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Maintain or improve code coverage

## Pull Request Process

1. Update README.md if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Request review from maintainers

## Questions?

Open an issue for discussion before starting major changes.
