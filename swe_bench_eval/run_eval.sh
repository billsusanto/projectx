#!/bin/bash

# Wrapper script for running evaluations with organized logging
# Usage: ./run_eval.sh <instance_id> [--force] [--foreground]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs/eval_logs"

# Parse arguments
INSTANCE_ID=""
FORCE=""
FOREGROUND=false

for arg in "$@"; do
    if [ "$arg" = "--force" ]; then
        FORCE="--force"
    elif [ "$arg" = "--foreground" ] || [ "$arg" = "-f" ]; then
        FOREGROUND=true
    elif [ -z "$INSTANCE_ID" ]; then
        INSTANCE_ID="$arg"
    fi
done

# Validate instance ID
if [ -z "$INSTANCE_ID" ]; then
    echo "❌ Error: Please provide a task instance ID"
    echo ""
    echo "Usage: ./run_eval.sh <instance_id> [--force] [--foreground]"
    echo ""
    echo "Options:"
    echo "  --force       Re-run evaluation even if already resolved"
    echo "  --foreground  Run in foreground (default: background with nohup)"
    echo ""
    echo "Available tasks:"
    ls -1 "$SCRIPT_DIR/tasks" 2>/dev/null | grep -v "^$" || echo "  (no tasks loaded yet)"
    exit 1
fi

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Set log file path
LOG_FILE="$LOG_DIR/${INSTANCE_ID}-eval.log"

# Run evaluation
if [ "$FOREGROUND" = true ]; then
    echo "🔄 Running evaluation in foreground..."
    echo "📝 Log: $LOG_FILE"
    ./run_evaluation.sh "$INSTANCE_ID" $FORCE 2>&1 | tee "$LOG_FILE"
else
    echo "🔄 Running evaluation in background..."
    echo "📝 Log: $LOG_FILE"
    echo ""
    nohup ./run_evaluation.sh "$INSTANCE_ID" $FORCE > "$LOG_FILE" 2>&1 &
    PID=$!
    echo "✅ Started with PID: $PID"
    echo ""
    echo "Monitor with:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "Check status:"
    echo "  ps -p $PID"
fi
