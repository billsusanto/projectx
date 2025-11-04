#!/bin/bash

# SWE-bench Evaluation Script
# Usage: ./run_evaluation.sh [instance_id] [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASKS_DIR="$SCRIPT_DIR/tasks"
REPORT_DIR="$SCRIPT_DIR/logs"
DATASET=princeton-nlp/SWE-bench_Lite
RESULTS_FILE="$REPORT_DIR/pydantic-agent.pydantic-test-final.json"

echo "🚀 Starting SWE-bench Evaluation"
echo "================================================"
echo ""

# Parse arguments
FORCE=false
INSTANCE_ID=""
for arg in "$@"; do
    if [ "$arg" = "--force" ]; then
        FORCE=true
    elif [ -z "$INSTANCE_ID" ]; then
        INSTANCE_ID="$arg"
    fi
done

# If instance ID provided, use that task's predictions file
if [ -n "$INSTANCE_ID" ]; then
    # Check if task is already resolved (unless --force is used)
    if [ "$FORCE" = false ] && [ -f "$RESULTS_FILE" ]; then
        if grep -q "\"$INSTANCE_ID\"" "$RESULTS_FILE"; then
            RESOLVED=$(python3 -c "import json; data=json.load(open('$RESULTS_FILE')); print('$INSTANCE_ID' in data.get('resolved_ids', []))")
            if [ "$RESOLVED" = "True" ]; then
                echo "✅ Task $INSTANCE_ID is already resolved (found in resolved_ids)"
                echo "⏭️  Skipping evaluation"
                echo ""
                echo "💡 To force re-evaluation, use: ./run_evaluation.sh $INSTANCE_ID --force"
                exit 0
            fi
        fi
    fi

    PREDICTIONS_PATH="$TASKS_DIR/$INSTANCE_ID/predictions.jsonl"
    if [ ! -f "$PREDICTIONS_PATH" ]; then
        echo "❌ Error: Predictions file not found at $PREDICTIONS_PATH"
        echo "💡 Make sure you have created predictions.jsonl in the task directory"
        exit 1
    fi
else
    # No instance ID - error out with helpful message
    echo "❌ Error: Please provide a task instance ID"
    echo ""
    echo "Usage: ./run_evaluation.sh <instance_id> [--force]"
    echo ""
    echo "Available tasks:"
    ls -1 "$TASKS_DIR" 2>/dev/null | grep -v "^$" || echo "  (no tasks loaded yet)"
    echo ""
    echo "💡 To load tasks, run: python load_task.py --count 5 --save"
    exit 1
fi

echo "📋 Task: $INSTANCE_ID"
echo "📋 Predictions: $PREDICTIONS_PATH"
echo "📊 Dataset: $DATASET"
echo "📁 Logs: $REPORT_DIR"
echo ""

# Create report directory
mkdir -p "$REPORT_DIR"

# Generate run ID with timestamp
RUN_ID="eval-$(date +%Y%m%d-%H%M%S)"

# Run evaluation for the specific task
echo "🎯 Evaluating task: $INSTANCE_ID"
echo "🆔 Run ID: $RUN_ID"
poetry run python -m swebench.harness.run_evaluation \
    -d "$DATASET" \
    -p "$PREDICTIONS_PATH" \
    -i "$INSTANCE_ID" \
    --report_dir "$REPORT_DIR" \
    --run_id "$RUN_ID" \
    --modal true

# Show results
echo ""
echo "================================================"
echo "✅ Evaluation complete!"
echo ""

if [ -f "$REPORT_DIR/results.json" ]; then
    echo "📊 Results:"
    cat "$REPORT_DIR/results.json"
else
    echo "⚠️  No results.json found yet. Check reports for errors."
fi

echo ""
echo "📁 Full reports at: $REPORT_DIR"
