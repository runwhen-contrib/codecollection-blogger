#!/usr/bin/env python
"""
Command-line interface for generating blog posts from tasks in the code collection.
"""

import os
import argparse
from pathlib import Path

from codecollection_blogger.fetch_codecollection import get_all_tasks_for_repository
from codecollection_blogger.blog_agent import create_blog_posts_from_tasks


def main():
    """Generate blog posts from tasks in the code collection."""
    parser = argparse.ArgumentParser(description="Generate blog posts from tasks in the code collection.")
    parser.add_argument(
        "--repo-url",
        default="https://github.com/runwhen-contrib/rw-cli-codecollection",
        help="URL of the code collection repository",
    )
    parser.add_argument("--output-dir", default="blog_posts", help="Directory to save the blog posts to")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of tasks to generate blog posts for")
    parser.add_argument("--tag-filter", default=None, help="Only generate blog posts for tasks with this tag")

    args = parser.parse_args()

    # Create the output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Get tasks from the repository
    print(f"Fetching tasks from {args.repo_url}...")
    tasks = get_all_tasks_for_repository(args.repo_url)
    print(f"Found {len(tasks)} tasks")

    # Filter tasks by tag if specified
    if args.tag_filter:
        tasks = [task for task in tasks if args.tag_filter in task.tags]
        print(f"Filtered to {len(tasks)} tasks with tag '{args.tag_filter}'")

    # Limit the number of tasks
    if args.limit and args.limit < len(tasks):
        tasks = tasks[: args.limit]
        print(f"Limited to {len(tasks)} tasks")

    # Create blog posts
    print(f"Generating blog posts in {args.output_dir}...")
    blog_post_paths = create_blog_posts_from_tasks(tasks, args.output_dir)

    print(f"Created {len(blog_post_paths)} blog posts in {args.output_dir}")

    # Print the paths to the generated blog posts
    print("\nGenerated blog posts:")
    for path in blog_post_paths:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
