#!/bin/bash
set -e

echo "========================================="
echo "Running JWT Authentication Tests"
echo "========================================="

# Navigate to backend directory
cd "$(dirname "$0")/.."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx pytest-html

# Verify NEXTAUTH_SECRET is set
if [ -z "$NEXTAUTH_SECRET" ]; then
    echo "ERROR: NEXTAUTH_SECRET environment variable is not set"
    exit 1
fi

# Export required environment variables
export JWT_ALGORITHM="HS256"

# Set Python path to current directory (backend/)
# This allows imports like 'from config import settings' to work
export PYTHONPATH="$(pwd):${PYTHONPATH}"

echo "Python path: $PYTHONPATH"
echo "Current directory: $(pwd)"

# Run tests with coverage and HTML report
echo "Running tests..."
python -m pytest tests/test_auth/ \
    -v \
    --cov=auth \
    --cov-report=html:htmlcov \
    --cov-report=xml:coverage.xml \
    --cov-report=term \
    --html=test-report.html \
    --self-contained-html \
    --junitxml=junit.xml

# Check test exit code
TEST_EXIT_CODE=$?

echo "========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
fi
echo "========================================="

exit $TEST_EXIT_CODE
