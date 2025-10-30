#!/bin/bash
# Simple memory test runner

echo "🧠 Running Memory Test for Financial Personal Assistant"
echo "======================================================="
echo ""

# Set AWS profile
export AWS_PROFILE=binbash

# Run the working memory test
uv run ./test_memory_final_working.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ Memory test completed successfully!"
else
    echo ""
    echo "⚠️ Memory test encountered issues."
fi

exit $exit_code