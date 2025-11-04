# SWE-bench Evaluation Suite

Complete environment for loading, solving, and evaluating SWE-bench tasks.

## Project Structure

```
swe_bench_eval/
├── load_task.py             # Load tasks from SWE-bench dataset
├── run_evaluation.sh        # Run evaluations with Modal
├── TESTING_GUIDE.md         # Guide for running tests
├── pyproject.toml           # Poetry dependencies
├── poetry.lock              # Locked dependencies
├── tasks/                   # Task workspace
│   └── <instance_id>/       # One directory per task
│       ├── task.json        # Task metadata
│       ├── prompt.txt       # Formatted task description
│       ├── repo/            # Cloned repository (optional)
│       ├── predictions.jsonl # Your fix for evaluation
│       └── *.patch          # Any patches you create
└── logs/                    # Evaluation logs and results
```

## Quick Start

### 1. Load Tasks

Load tasks from the SWE-bench dataset:

```bash
# Load 5 tasks (metadata only)
python load_task.py --count 5 --save

# Load 5 tasks with repositories cloned
python load_task.py --count 5 --save --clone-repo

# Load a specific task
python load_task.py --task-id astropy__astropy-12907 --save --clone-repo

# View available options
python load_task.py --help
```

**Options:**
- `--count N` - Load N tasks (default: 1)
- `--task-id ID` - Load specific task by instance ID
- `--split` - Choose "test", "dev", or "train" (default: test)
- `--no-lite` - Use full SWE-bench instead of Lite (300 vs 2,294 tasks)
- `--save` - Save tasks to ./tasks directory
- `--clone-repo` - Clone repositories (requires --save)

### 2. Work on a Task

Each task is in its own directory with everything you need:

```bash
# Navigate to task
cd tasks/astropy__astropy-12907

# Read the task description
cat prompt.txt

# View task metadata
cat task.json

# Work in the repository (if cloned)
cd repo
# ... make your changes ...

# Create a patch
git diff > ../fix.patch
```

### 3. Create Predictions

Create `predictions.jsonl` in the task directory:

```jsonl
{"instance_id": "astropy__astropy-12907", "model_patch": "diff --git a/file.py...", "model_name_or_path": "my-agent"}
```

### 4. Run Evaluation

```bash
# Evaluate a specific task
./run_evaluation.sh astropy__astropy-12907

# List available tasks
ls tasks/
```

## What Happens During Evaluation

The evaluation harness (running on Modal):
1. Spins up isolated Docker container
2. Clones repository at correct base commit
3. Applies your patch from predictions.jsonl
4. Installs dependencies
5. Runs test suite
6. Returns pass/fail result

## Task Workflow

### Complete Example

```bash
# 1. Load a task
python load_task.py --task-id django__django-11099 --save --clone-repo

# 2. Explore the task
cd tasks/django__django-11099
cat prompt.txt

# 3. Work on the fix
cd repo
# ... analyze code, make changes ...
git diff > ../my_fix.patch

# 4. Create predictions file
cd ..
cat > predictions.jsonl << EOF
{"instance_id": "django__django-11099", "model_patch": "$(cat my_fix.patch)", "model_name_or_path": "manual"}
EOF

# 5. Run evaluation
cd ../..
./run_evaluation.sh django__django-11099

# 6. Check results
cat logs/*.json
```

## Dependencies

- **swebench** (4.1.0) - SWE-bench evaluation harness
- **modal** (1.2.1) - Cloud compute for isolated testing
- **datasets** (4.3.0) - Load SWE-bench tasks
- **Poetry** - Dependency management

## Troubleshooting

**Modal authentication fails:**
```bash
poetry run modal setup
```

**Can't find task:**
```bash
ls tasks/
python load_task.py --task-id <instance-id> --save
```

**Evaluation fails:**
- Ensure predictions.jsonl exists in task directory
- Check predictions.jsonl format
- Verify patch applies cleanly
- Check Modal logs

## Useful Commands

```bash
# Activate Poetry environment
poetry shell

# Update dependencies
poetry update

# View loaded tasks
ls tasks/

# Check Modal status
poetry run modal profile current
```

## Cost Estimates (Modal)

- Free tier: $30/month credit
- Single task: ~$0.001-0.01
- 10 tasks: ~$0.01-0.10
- Full SWE-bench_Lite (300 tasks): ~$3-10

## Links

- [SWE-bench](https://github.com/princeton-nlp/SWE-bench)
- [Modal Dashboard](https://modal.com)
- [SWE-bench_Lite Dataset](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite)
