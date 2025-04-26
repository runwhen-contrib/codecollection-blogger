from dataclasses import dataclass
import tempfile
import subprocess
import os
import re
import json
import hashlib
from pathlib import Path
from robot.api import TestSuiteBuilder
from typing import List, Optional, Dict, Any


@dataclass
class CodeCollection:
    pass


@dataclass
class TaskSourceCode:
    """
    Represents the source code and metadata for a task in a codecollection.
    """

    name: str
    tags: List[str]
    documentation: str
    source_code: Optional[str] = None
    supporting_files_url: Optional[str] = None
    supporting_files: Dict[str, str] = None

    def __post_init__(self):
        if self.supporting_files is None:
            self.supporting_files = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the TaskSourceCode object to a dictionary for serialization.

        Returns:
            Dict[str, Any]: A dictionary representation of the TaskSourceCode object
        """
        return {
            "name": self.name,
            "tags": self.tags,
            "documentation": self.documentation,
            "source_code": self.source_code,
            "supporting_files_url": self.supporting_files_url,
            "supporting_files": self.supporting_files,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSourceCode":
        """
        Create a TaskSourceCode object from a dictionary.

        Args:
            data: A dictionary containing the TaskSourceCode data

        Returns:
            TaskSourceCode: A new TaskSourceCode object
        """
        return cls(
            name=data["name"],
            tags=data["tags"],
            documentation=data["documentation"],
            source_code=data.get("source_code"),
            supporting_files_url=data.get("supporting_files_url"),
            supporting_files=data.get("supporting_files", {}),
        )


def fetch_codecollection_repository_contents(repo_url: str) -> Path:
    """
    Fetches the contents of a code collection repository to a temporary directory.

    Args:
        repo_url: The URL of the git repository to fetch

    Returns:
        Path: The path to the temporary directory containing the cloned repository
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    try:
        # Clone the repository
        subprocess.run(["git", "clone", repo_url, str(temp_path)], check=True, capture_output=True, text=True)
        print(f"Successfully cloned repository to {temp_path}")
        return temp_path
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e.stderr}")
        raise


def extract_test_source_code(test) -> str:
    """
    Extract the source code of a Robot Framework test.

    Args:
        test: The Robot Framework test object

    Returns:
        str: The source code of the test
    """
    if not hasattr(test, "body") or not test.body:
        return "No source code available"

    # Convert the test body to a string representation
    source_lines = []

    # Add test name and documentation
    source_lines.append(f"*** Test Case ***")
    source_lines.append(f"{test.name}")
    if hasattr(test, "doc") and test.doc:
        source_lines.append(f"    [Documentation]    {test.doc}")

    # Add tags if available
    if hasattr(test, "tags") and test.tags:
        tags_str = "    ".join(test.tags)
        source_lines.append(f"    [Tags]    {tags_str}")

    # Add test steps
    for keyword in test.body:
        if hasattr(keyword, "name"):
            # Get the keyword name and arguments
            keyword_name = keyword.name
            args = []
            if hasattr(keyword, "args"):
                args = [str(arg) for arg in keyword.args]

            # Format the keyword call
            keyword_call = f"    {keyword_name}"
            if args:
                keyword_call += "    " + "    ".join(args)

            source_lines.append(keyword_call)

    return "\n".join(source_lines)


def find_bash_file_references(source_code: str) -> List[str]:
    """
    Find references to bash files in the source code.

    Args:
        source_code: The source code to search for bash file references

    Returns:
        List[str]: A list of bash file names referenced in the source code
    """
    # Look for patterns like "Run Bash File" or similar that might reference a bash file
    bash_file_pattern = r"Run\s+Bash\s+File\s+([^\s]+)"
    matches = re.findall(bash_file_pattern, source_code, re.IGNORECASE)
    return matches


def parse_codecollection_repository_contents(repo_path: str) -> List[TaskSourceCode]:
    """
    Parse the contents of a codecollection repository and return a list of TaskSourceCode objects.

    Args:
        repo_path (str): Path to the repository

    Returns:
        List[TaskSourceCode]: List of TaskSourceCode objects
    """
    tasks = []
    codebundles_dir = os.path.join(repo_path, "codebundles")

    if not os.path.exists(codebundles_dir):
        return tasks

    for codebundle in os.listdir(codebundles_dir):
        codebundle_path = os.path.join(codebundles_dir, codebundle)
        if not os.path.isdir(codebundle_path):
            continue

        runbook_path = os.path.join(codebundle_path, "runbook.robot")
        if not os.path.exists(runbook_path):
            continue

        try:
            suite = TestSuiteBuilder().build(runbook_path)
            for test in suite.tests:
                # Convert Robot Framework Tags object to list of strings
                tags = [str(tag) for tag in test.tags]

                task = TaskSourceCode(
                    name=test.name,
                    tags=tags,
                    documentation=test.doc or "",
                    source_code=extract_test_source_code(test),
                    supporting_files_url=f"https://github.com/runwhen-contrib/rw-codecollection/tree/main/codebundles/{codebundle}",
                )
                tasks.append(task)
        except Exception as e:
            print(f"Error parsing {runbook_path}: {e}")

    return tasks


def get_cache_dir() -> Path:
    """
    Get the directory where cached TaskSourceCode objects are stored.

    Returns:
        Path: The path to the cache directory
    """
    # Create a cache directory in the user's home directory
    cache_dir = Path.home() / ".codecollection_blogger" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_repo_cache_key(repo_url: str, codebundle_name: Optional[str] = None) -> str:
    """
    Generate a cache key for a repository or codebundle.

    Args:
        repo_url: The URL of the repository
        codebundle_name: The name of the codebundle (optional)

    Returns:
        str: A cache key for the repository or codebundle
    """
    # Create a hash of the repository URL
    repo_hash = hashlib.md5(repo_url.encode()).hexdigest()

    if codebundle_name:
        # If a codebundle name is provided, include it in the cache key
        return f"{repo_hash}_{codebundle_name}"
    else:
        # Otherwise, just use the repository hash
        return repo_hash


def cache_tasks(tasks: List[TaskSourceCode], repo_url: str, codebundle_name: str) -> None:
    """
    Cache TaskSourceCode objects to disk.

    Args:
        tasks: A list of TaskSourceCode objects to cache
        repo_url: The URL of the repository
        codebundle_name: The name of the codebundle
    """
    cache_dir = get_cache_dir()
    cache_key = get_repo_cache_key(repo_url, codebundle_name)
    cache_file = cache_dir / f"{cache_key}.json"

    # Convert TaskSourceCode objects to dictionaries
    task_dicts = [task.to_dict() for task in tasks]

    # Write to cache file
    with open(cache_file, "w") as f:
        json.dump(task_dicts, f, indent=2)

    print(f"Cached {len(tasks)} tasks for {codebundle_name} to {cache_file}")


def get_cached_tasks(repo_url: str, codebundle_name: str) -> List[TaskSourceCode]:
    """
    Retrieve cached TaskSourceCode objects from disk.

    Args:
        repo_url: The URL of the repository
        codebundle_name: The name of the codebundle

    Returns:
        List[TaskSourceCode]: A list of cached TaskSourceCode objects, or an empty list if not found
    """
    cache_dir = get_cache_dir()
    cache_key = get_repo_cache_key(repo_url, codebundle_name)
    cache_file = cache_dir / f"{cache_key}.json"

    if not cache_file.exists():
        return []

    try:
        with open(cache_file, "r") as f:
            task_dicts = json.load(f)

        # Convert dictionaries to TaskSourceCode objects
        tasks = [TaskSourceCode.from_dict(task_dict) for task_dict in task_dicts]
        print(f"Retrieved {len(tasks)} cached tasks for {codebundle_name}")
        return tasks
    except Exception as e:
        print(f"Error reading cache file: {e}")
        return []


def get_all_tasks_for_repository(repo_url: str, use_cache: bool = True) -> List[TaskSourceCode]:
    """
    Get all TaskSourceCode objects for a repository.

    Args:
        repo_url: The URL of the repository
        use_cache: Whether to use cached results if available

    Returns:
        List[TaskSourceCode]: A list of all TaskSourceCode objects for the repository
    """
    all_tasks = []
    cache_dir = get_cache_dir()
    repo_hash = get_repo_cache_key(repo_url)

    # Check if we have a cache file for the entire repository
    repo_cache_file = cache_dir / f"{repo_hash}.json"

    if use_cache and repo_cache_file.exists():
        try:
            with open(repo_cache_file, "r") as f:
                task_dicts = json.load(f)

            # Convert dictionaries to TaskSourceCode objects
            all_tasks = [TaskSourceCode.from_dict(task_dict) for task_dict in task_dicts]
            print(f"Retrieved {len(all_tasks)} cached tasks for repository")
            return all_tasks
        except Exception as e:
            print(f"Error reading repository cache file: {e}")

    # If we don't have a cache file for the entire repository, fetch and parse the repository
    repo_path = fetch_codecollection_repository_contents(repo_url)

    # Parse the repository contents
    all_tasks = parse_codecollection_repository_contents(repo_path)

    # Cache the results
    task_dicts = [task.to_dict() for task in all_tasks]
    with open(repo_cache_file, "w") as f:
        json.dump(task_dicts, f, indent=2)

    print(f"Cached {len(all_tasks)} tasks for repository to {repo_cache_file}")

    return all_tasks


if __name__ == "__main__":
    repo_url = "https://github.com/runwhen-contrib/rw-cli-codecollection"
    try:
        repo_path = fetch_codecollection_repository_contents(repo_url)
        print(f"Repository contents are available at: {repo_path}")

        # Parse the repository contents
        tasks = parse_codecollection_repository_contents(repo_path)
        print(f"\nFound {len(tasks)} tasks across all codebundles")

        # Cache the tasks for each codebundle
        codebundles = {}
        for task in tasks:
            # Extract codebundle name from the supporting_files_url
            if task.supporting_files_url:
                # The URL format is: https://github.com/runwhen-contrib/rw-cli-codecollection/tree/main/codebundles/{codebundle_name}
                parts = task.supporting_files_url.split("/")
                if len(parts) >= 8:
                    codebundle_name = parts[-1]
                    if codebundle_name not in codebundles:
                        codebundles[codebundle_name] = []
                    codebundles[codebundle_name].append(task)

        # Cache tasks for each codebundle
        for codebundle_name, codebundle_tasks in codebundles.items():
            cache_tasks(codebundle_tasks, repo_url, codebundle_name)

        # Cache all tasks for the repository
        cache_tasks(tasks, repo_url, None)

        # Print a sample of the first few tasks with their source code
        if tasks:
            print("\nSample tasks:")
            for i, task in enumerate(tasks[:2]):
                print(f"\nTask {i+1}: {task.name}")
                print(f"Tags: {', '.join(task.tags) if task.tags else 'None'}")
                print(
                    f"Documentation: {task.documentation[:100]}..."
                    if len(task.documentation) > 100
                    else f"Documentation: {task.documentation}"
                )
                print(f"Supporting files URL: {task.supporting_files_url}")

                # Print supporting files if any
                if task.supporting_files:
                    print("\nSupporting Files:")
                    for filename, contents in task.supporting_files.items():
                        print(f"  - {filename}")

                print("\nSource Code:")
                print("-" * 80)
                print(task.source_code)
                print("-" * 80)
    except Exception as e:
        print(f"Failed to fetch repository: {e}")
