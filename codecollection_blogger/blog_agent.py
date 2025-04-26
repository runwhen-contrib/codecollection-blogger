from typing import Dict, Any, List, Optional, TypedDict, OrderedDict
import os
import re
from datetime import datetime
from pathlib import Path

from langgraph.graph import Graph, StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from codecollection_blogger.types import BlogPostState
from codecollection_blogger.blog_agent_nodes.write_intro_paragraph_node import write_intro_paragraph, IntroResponse
from codecollection_blogger.blog_agent_nodes.write_blog_post_node import write_blog_post
from codecollection_blogger.blog_agent_nodes.write_issues_paragraphs_node import write_issues_paragraphs
from codecollection_blogger.blog_agent_nodes.write_atc_paragraph_node import write_atc_paragraph
from codecollection_blogger.fetch_codecollection import TaskSourceCode


def format_blog_post(state: BlogPostState) -> BlogPostState:
    """
    Format the blog post using the state information.

    Args:
        state: The current state of the blog post generation workflow

    Returns:
        BlogPostState: The updated state with the formatted blog post
    """
    task = state["task"]
    title = state["title"]

    # Format tags for display
    tags_display = ", ".join([f"`{tag}`" for tag in task.tags])

    # Format all paragraphs into sections
    content_sections = []
    if state.get("raw_paragraphs"):
        for paragraph in state["raw_paragraphs"]:
            if paragraph.header:
                content_sections.append(f"## {paragraph.header}\n\n{paragraph.body}\n")
            else:
                content_sections.append(f"{paragraph.body}\n")

    # Join all sections with proper spacing
    content = "\n".join(content_sections)

    # Create the blog post content
    blog_post = f"""---
title: "{title}"
date: {datetime.now().strftime('%Y-%m-%d')}
tags: [{", ".join(task.tags)}]
---

# {title}

## Tags

{tags_display}

{content}

## Source Code

```robotframework
{task.source_code}
```

## Supporting Files

This task is part of the [RunWhen Code Collection]({task.supporting_files_url}).
"""

    state["blog_post"] = blog_post
    return state


def save_blog_post(state: BlogPostState, output_dir: Optional[str] = None) -> BlogPostState:
    """
    Save the blog post to a file.

    Args:
        state: The current state of the blog post generation workflow
        output_dir: Optional directory to save the blog post to

    Returns:
        BlogPostState: The updated state
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{state['slug']}.md")
        with open(output_path, "w") as f:
            f.write(state["blog_post"])
        print(f"Blog post saved to {output_path}")

    return state


def create_blog_post_workflow(output_dir: Optional[str] = None) -> Graph:
    """
    Create a workflow for generating blog posts.

    Args:
        output_dir: Optional directory to save the blog post to

    Returns:
        Graph: The workflow graph
    """
    # Create the workflow
    workflow = StateGraph(BlogPostState)

    # Add nodes
    workflow.add_node("write_intro", write_intro_paragraph)
    workflow.add_node("write_atc", write_atc_paragraph)

    workflow.add_node("write_issues", write_issues_paragraphs)
    workflow.add_node("format_post", format_blog_post)
    workflow.add_node("save_post", lambda state: save_blog_post(state, output_dir))

    # Add edges
    workflow.add_edge("write_intro", "write_atc")
    workflow.add_edge("write_atc", "write_issues")
    workflow.add_edge("write_issues", "format_post")
    workflow.add_edge("format_post", "save_post")

    # Set the entry point
    workflow.set_entry_point("write_intro")

    # Set the exit point
    workflow.set_finish_point("save_post")

    # Compile the workflow
    return workflow.compile()


def create_task_blog_post_from_task_source_code(
    task: TaskSourceCode,
    output_dir: Optional[str] = None,
    template_path: Optional[str] = None,
) -> str:
    """
    Create a blog post from a TaskSourceCode object.

    Args:
        task: The TaskSourceCode object to create a blog post from
        output_dir: Optional directory to save the blog post to
        template_path: Optional path to a template file to use for the blog post

    Returns:
        str: The content of the generated blog post
    """
    # Extract task name and create a slug
    task_name = task.name
    slug = re.sub(r"[^\w\s-]", "", task_name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-_")

    # Create a title from the task name
    title = task_name.replace("${", "\\${").replace("}", "\\}")

    # Create the initial state
    initial_state: BlogPostState = {
        "task": task,
        "title": title,
        "slug": slug,
        "blog_post": "",
        "raw_paragraphs": [],
        "enriched_issues": [],
    }

    # Create and run the workflow
    workflow = create_blog_post_workflow(output_dir)
    final_state = workflow.invoke(initial_state)

    return final_state["blog_post"]


def create_blog_posts_from_tasks(
    tasks: List[TaskSourceCode],
    output_dir: str,
) -> List[str]:
    """
    Create blog posts from a list of TaskSourceCode objects.

    Args:
        tasks: List of TaskSourceCode objects to create blog posts from
        output_dir: Directory to save the blog posts to

    Returns:
        List[str]: List of paths to the generated blog posts
    """
    blog_post_paths = []
    blog_posts = []

    for task in tasks:
        # Create a slug from the task name
        task_name = task.name
        slug = re.sub(r"[^\w\s-]", "", task_name.lower())
        slug = re.sub(r"[-\s]+", "-", slug).strip("-_")

        # Create the blog post
        blog_post = create_task_blog_post_from_task_source_code(task)
        blog_posts.append(blog_post)
        # Save the blog post
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{slug}.md")
        with open(output_path, "w") as f:
            f.write(blog_post)

        blog_post_paths.append(output_path)

    return blog_posts


if __name__ == "__main__":
    # Example usage
    from codecollection_blogger.fetch_codecollection import get_all_tasks_for_repository

    # Get tasks from the repository
    repo_url = "https://github.com/runwhen-contrib/rw-cli-codecollection"
    tasks = get_all_tasks_for_repository(repo_url)

    # Create blog posts for the first 5 tasks using the BlogAgent
    output_dir = "blog_posts"
    results = create_blog_posts_from_tasks(tasks[:5], output_dir=output_dir)

    print(f"\nCreated {len(results)} blog posts in {output_dir}")

    # Print a summary of the generated content
    print("\nGeneration Summary:")
    for i, result in enumerate(results, 1):
        print(f"\nBlog Post {i}:")
        print(result)
        print("-" * 80)
