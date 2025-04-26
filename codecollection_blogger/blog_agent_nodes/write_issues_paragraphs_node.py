from typing import Dict, List, OrderedDict, Optional
from dataclasses import dataclass
import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from codecollection_blogger.types import (
    BlogPostState,
    BlogParagraph,
    PARAGRAPH_TYPE_ISSUE,
    BasicIssue,
    EnrichedIssue,
)
from codecollection_blogger.fetch_codecollection import TaskSourceCode
from codecollection_blogger.blog_agent_nodes.llm import initialize_llm


def clean_json_response(content: str) -> str:
    """Remove markdown code block markers and clean whitespace from JSON response."""
    # Remove markdown code block markers if present
    content = re.sub(r"^```json\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    # Clean any leading/trailing whitespace
    return content.strip()


# System prompt for the LLM
SYSTEM_PROMPT = """You are a technical writer specializing in Kubernetes and cloud infrastructure. Your task is to analyze issues and write clear, informative paragraphs about them."""

# Additional system prompt for issue enrichment
ENRICH_SYSTEM_PROMPT = """You are an expert in Robot Framework and Kubernetes automation.
Your task is to analyze Robot Framework test code and identify potential issues that would be raised,
focusing on set_issue_title and set_issue_details patterns."""

# Human prompt template
ENRICH_ISSUE_TEMPLATE = """Analyze this Kubernetes automation issue and provide detailed insights.

Issue Title: {issue_title}
Issue Details: {issue_details}
Issue Trigger Condition: {issue_trigger_condition}
Issue Severity: {issue_severity}

Format your response as a JSON object with these exact keys:
1. "problem_statement": A clear 1-2 sentence explanation of when the issue may occur
2. "impact": A 1-2 sentence description of why this issue matters and its potential impact
3. "resolution": A 1-2 sentence summary of how to resolve or prevent this issue if it does occur
4. "revised_title": A revised title that frames this as an issue that may possibly occur in the future, removing any of the template tags ("${{...}}")
Example format:
{{
    "problem_statement": "The unhealthy GCE ingress backend issue could occur when the Google Cloud Load Balancer cannot successfully communicate with your Kubernetes service endpoints.",
    "impact": "This can lead to service disruption for end users, as traffic may not be properly routed to healthy backend pods. In production environments, this directly affects application availability and user experience.",
    "resolution": "To resolve this, verify that the GCP health check configuration matches your Kubernetes service's readiness probe settings, and ensure network policies allow health check requests. Regular monitoring using this automation task can help catch potential issues early.",
    "revised_title": "Unhealthy GCE ingress backend may be detected in namespace"
}}"""

# Human prompt template for issue enrichment
IDENTIFY_ISSUES_TEMPLATE = """Analyze this Robot Framework test code and identify the issues that would be raised.
Focus on lines containing 'set_issue_title' and 'set_issue_details' to understand what issues this automation detects.

Task Name: {task_name}
Task Documentation: {task_documentation}

Source Code:
```robotframework
{source_code}
```

Format your response as a JSON object with an "issues" key containing an array of objects with these exact keys:
- "title": The pattern used in set_issue_title
- "details": The pattern used in set_issue_details
- "trigger_condition": A clear description of when this issue would be raised
- "severity": The severity level (extract from set_severity_level if present, otherwise "unknown")

Example format:
{{
    "issues": [
        {{
            "title": "Unhealthy GCE ingress backend detected in namespace",
            "details": "The following backend services are reporting unhealthy status",
            "trigger_condition": "When the health check response indicates an unhealthy backend service",
            "severity": "3"
        }}
    ]
}}"""


def create_issues_table(issues: List[EnrichedIssue]) -> str:
    """Create a markdown table summarizing the basic issues.

    Args:
        issues: List of BasicIssue objects

    Returns:
        str: Markdown formatted table
    """
    if not issues:
        return ""

    table = ["| Issue | Trigger Condition |", "|-------|---------|------------------|"]

    for issue in issues:
        # Escape any | characters in the text to avoid breaking table formatting
        title = issue.revised_title.replace("|", "\\|")
        trigger = issue.trigger_condition.replace("|", "\\|")

        row = f"| {title} | {trigger} |"
        table.append(row)

    return "\n".join(table)


def write_issues_paragraphs(state: BlogPostState) -> BlogPostState:
    """
    Write detailed paragraphs about each issue detected by the automation task.
    Each issue will have a problem statement, impact analysis, and resolution summary.
    """
    if "raw_paragraphs" not in state:
        state["raw_paragraphs"] = []

    # Initialize LLM with explicit JSON response format
    llm = initialize_llm(response_format="json_object")

    basic_issues = identify_issues(state["task"])
    if not basic_issues:
        return state

    for basic_issue in basic_issues:
        # Format the human prompt with issue details
        human_prompt = ENRICH_ISSUE_TEMPLATE.format(
            issue_title=basic_issue.title,
            issue_details=basic_issue.details,
            issue_trigger_condition=basic_issue.trigger_condition,
            issue_severity=basic_issue.severity,
        )

        # Get response from LLM
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=human_prompt)]
        enriched_issues = []
        try:
            response = llm.invoke(messages)
            response_data = json.loads(response.content)
            enriched_issue = EnrichedIssue.from_dict_with_basic(response_data, basic_issue)
            enriched_issues.append(enriched_issue)

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response for issue {basic_issue.title}: {e}")
            print(f"Response data: {response.content}")
            continue
        except KeyError as e:
            print(f"Missing key in response for issue {basic_issue.title}: {e}")
            print(f"Response data: {response_data}")
            continue

    # Add issues summary table to the response
    issues_table = create_issues_table(enriched_issues)
    summary_paragraph = BlogParagraph(paragraph_type=PARAGRAPH_TYPE_ISSUE, header="Issues Summary", body=issues_table)
    state["raw_paragraphs"].append(summary_paragraph)
    # Create blog paragraphs from the response
    for enriched_issue in enriched_issues:
        problem_paragraph = BlogParagraph(
            paragraph_type=PARAGRAPH_TYPE_ISSUE,
            header=f"Problem: {enriched_issue.revised_title}",
            body=enriched_issue.problem_statement,
        )
        state["raw_paragraphs"].append(problem_paragraph)
        impact_paragraph = BlogParagraph(
            paragraph_type=PARAGRAPH_TYPE_ISSUE, header="Impact", body=enriched_issue.impact
        )
        state["raw_paragraphs"].append(impact_paragraph)
        resolution_paragraph = BlogParagraph(
            paragraph_type=PARAGRAPH_TYPE_ISSUE, header="Resolution", body=enriched_issue.resolution
        )
        state["raw_paragraphs"].append(resolution_paragraph)

    return state


def identify_issues(task: TaskSourceCode) -> List[BasicIssue]:
    """
    Analyze the Robot Framework test code to identify and enrich issue patterns.

    Args:
        task: The TaskSourceCode object containing the Robot Framework test

    Returns:
        List[EnrichedIssues]: A list of enriched issue descriptions
    """
    # Format the prompt with task details
    human_prompt = IDENTIFY_ISSUES_TEMPLATE.format(
        task_name=task.name,
        task_documentation=task.documentation,
        source_code=task.source_code,
    )

    messages = [
        SystemMessage(content=ENRICH_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    try:
        # Initialize LLM with explicit JSON response format
        llm = initialize_llm(response_format="json_object")
        response = llm.invoke(messages)

        # Parse the JSON array response
        response_dict = json.loads((response.content))
        issues_list = response_dict["issues"]

        # Convert each issue dict to a BasicIssue object
        basic_issues_list = [BasicIssue.from_dict(issue) for issue in issues_list]  # type: ignore

        return basic_issues_list

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response content was: {response.content}")
        return []
    except Exception as e:
        print(f"Unexpected error in identify_issues: {e}")
        return []


if __name__ == "__main__":
    from codecollection_blogger.fetch_codecollection import get_all_tasks_for_repository

    # Get tasks from the repository
    repo_url = "https://github.com/runwhen-contrib/rw-cli-codecollection"
    tasks = get_all_tasks_for_repository(repo_url)

    # Process the first task only for testing
    task = tasks[0]
    print(f"\n{'='*80}")
    print(f"Processing task: {task.name}")
    print(f"Documentation: {task.documentation}")
    print(f"Tags: {', '.join(task.tags)}")
    print(f"Source Code Preview:")
    print(f"{task.source_code[:500]}...")
    print(f"{'='*80}\n")

    print("Testing write_issues_paragraphs...")

    # Create initial state with proper TypedDict structure
    initial_state: BlogPostState = {
        "task": task,
        "title": task.name.replace("${", "\\${").replace("}", "\\}"),
        "slug": "",  # Not needed for testing
        "blog_post": "",
        "raw_paragraphs": [],
        "enriched_issues": [],  # Initialize empty list for enriched issues
    }

    try:
        # Generate the issues paragraphs
        result = write_issues_paragraphs(initial_state)

        if result["raw_paragraphs"]:
            print("\nSuccessfully generated issues analysis:")

            print("\nDetailed Issue Analysis:")
            for paragraph in result["raw_paragraphs"]:
                print(f"\n{paragraph.header}")
                print(paragraph.body)
        else:
            print("\nNo paragraphs were generated")

    except Exception as e:
        print(f"\nError processing task: {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            print(f"Caused by: {e.__cause__}")

    print("\nTest completed.")
