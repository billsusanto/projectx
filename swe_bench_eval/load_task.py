"""
Lightweight SWE-bench Task Loader
Loads task descriptions from SWE-bench dataset for agent testing
"""

from datasets import load_dataset
import json
import os
import argparse

def load_swe_bench_task(task_id=None, split="test", lite=True):
    """
    Load a task from SWE-bench dataset

    Args:
        task_id: Specific task ID to load (e.g., "django__django-11099")
        split: Dataset split ("test", "dev", "train")
        lite: Use SWE-bench_Lite (smaller, curated subset)

    Returns:
        dict: Task information including problem statement, code, hints
    """
    dataset_name = "princeton-nlp/SWE-bench_Lite" if lite else "princeton-nlp/SWE-bench"

    print(f"Loading {dataset_name}...")
    dataset = load_dataset(dataset_name, split=split)

    if task_id:
        # Find specific task
        task = next((item for item in dataset if item['instance_id'] == task_id), None)
        if not task:
            print(f"Task {task_id} not found!")
            return None
    else:
        # Get first task
        task = dataset[0]

    return task

def load_multiple_tasks(count=1, split="test", lite=True):
    """
    Load multiple tasks from SWE-bench dataset

    Args:
        count: Number of tasks to load (default: 5)
        split: Dataset split ("test", "dev", "train")
        lite: Use SWE-bench_Lite (smaller, curated subset)

    Returns:
        list: List of task dictionaries
    """
    dataset_name = "princeton-nlp/SWE-bench_Lite" if lite else "princeton-nlp/SWE-bench"

    print(f"Loading {count} tasks from {dataset_name}...")
    dataset = load_dataset(dataset_name, split=split)

    # Ensure we don't try to load more tasks than available
    num_tasks = min(count, len(dataset))
    tasks = [dataset[i] for i in range(num_tasks)]

    print(f"Loaded {num_tasks} tasks")
    return tasks

def format_task_for_agent(task):
    """Format task into a clear prompt for the agent"""

    prompt = f"""
# SWE-bench Task: {task['instance_id']}

**Repository:** {task['repo']}
**Base Commit:** {task['base_commit']}

## Problem Statement

{task['problem_statement']}

## Hints (if needed)

{task.get('hints_text', 'No hints provided')}

## Your Task

1. Explore the codebase to understand the issue
2. Locate the relevant files mentioned in the problem
3. Analyze the code and identify what needs to be changed
4. Implement a fix for the issue
5. Explain your solution

Note: You're working in a sandbox environment. The actual repository code needs to be set up manually.
"""

    return prompt

def save_task_info(task, output_dir="./tasks", clone_repo=False):
    """Save task information to a JSON file in organized subdirectory"""
    import subprocess

    # Create subdirectory for this specific task
    task_dir = os.path.join(output_dir, task['instance_id'])
    os.makedirs(task_dir, exist_ok=True)

    # Save task JSON
    task_file = os.path.join(task_dir, "task.json")
    with open(task_file, 'w') as f:
        json.dump(task, f, indent=2)

    # Save formatted prompt
    agent_prompt = format_task_for_agent(task)
    prompt_file = os.path.join(task_dir, "prompt.txt")
    with open(prompt_file, 'w') as f:
        f.write(agent_prompt)

    # Clone repository if requested
    if clone_repo:
        repo_dir = os.path.join(task_dir, "repo")
        if not os.path.exists(repo_dir):
            print(f"  Cloning repository {task['repo']}...")
            repo_url = f"https://github.com/{task['repo']}.git"
            try:
                subprocess.run(['git', 'clone', repo_url, repo_dir],
                             check=True, capture_output=True)
                # Checkout the base commit
                subprocess.run(['git', 'checkout', task['base_commit']],
                             cwd=repo_dir, check=True, capture_output=True)
                print(f"  Repository cloned and checked out to {task['base_commit'][:7]}")
            except subprocess.CalledProcessError as e:
                print(f"  Warning: Failed to clone repository: {e}")
        else:
            print(f"  Repository already exists, skipping clone")

    print(f"Task saved to: {task_dir}/")
    return task_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load tasks from SWE-bench dataset")
    parser.add_argument("--count", type=int, default=1, help="Number of tasks to load (default: 1)")
    parser.add_argument("--task-id", type=str, help="Specific task ID to load (e.g., django__django-11099)")
    parser.add_argument("--split", type=str, default="test", choices=["test", "dev", "train"],
                        help="Dataset split (default: test)")
    parser.add_argument("--no-lite", action="store_true", help="Use full SWE-bench instead of Lite")
    parser.add_argument("--save", action="store_true", help="Save tasks to ./tasks directory")
    parser.add_argument("--clone-repo", action="store_true", help="Clone the repository for each task (requires --save)")

    args = parser.parse_args()

    # Validate arguments
    if args.clone_repo and not args.save:
        parser.error("--clone-repo requires --save")

    lite = not args.no_lite

    # Load specific task or multiple tasks
    if args.task_id:
        print(f"Loading task {args.task_id}...")
        task = load_swe_bench_task(task_id=args.task_id, split=args.split, lite=lite)

        if task:
            print(f"\nTask ID: {task['instance_id']}")
            print(f"Repository: {task['repo']}")
            print(f"\nProblem Statement Preview:")
            print(task['problem_statement'][:300] + "...")

            if args.save:
                save_task_info(task, clone_repo=args.clone_repo)
    else:
        # Load multiple tasks
        tasks = load_multiple_tasks(count=args.count, split=args.split, lite=lite)

        print(f"\n{'='*80}")
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task['instance_id']}")
            print(f"   Repository: {task['repo']}")
            print(f"   Problem: {task['problem_statement'][:100].strip()}...")
            print()

            if args.save:
                save_task_info(task, clone_repo=args.clone_repo)

        if args.save:
            print(f"\n{'='*80}")
            print(f"All tasks saved to ./tasks/ directory")
            if args.clone_repo:
                print(f"Each task has its own subdirectory with task.json, prompt.txt, and cloned repo/")
            else:
                print(f"Each task has its own subdirectory with task.json and prompt.txt")
                print(f"Tip: Use --clone-repo to also clone repositories automatically")
