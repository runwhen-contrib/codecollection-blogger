from typing import Dict, List, Optional
from dataclasses import dataclass
import json

from langchain_core.messages import HumanMessage, SystemMessage

from codecollection_blogger.types import BlogPostState, BlogParagraph, PARAGRAPH_TYPE_INTRO
from codecollection_blogger.fetch_codecollection import TaskSourceCode
from codecollection_blogger.blog_agent_nodes.llm import initialize_llm


@dataclass
class Scenario:
    task_name: str
    task_documentation: str
    task_tags: List[str]


@dataclass
class IntroResponse:
    hook: str
    context: str
    value_proposition: str

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "IntroResponse":
        return cls(hook=data["hook"], context=data["context"], value_proposition=data["value_proposition"])


# System prompt for the LLM
SYSTEM_PROMPT = """You are a technical writer creating engaging blog post introductions."""

# Human prompt template
HUMAN_PROMPT_TEMPLATE = """You are a technical writer creating a blog post about a Kubernetes automation task.
Write an engaging introduction paragraph that consists of three parts:

1. A hook that describes a common support ticket, alert, incident, or help request that this automation task helps solve
2. Context that explains the problem space
3. A value proposition that explains why this automation is valuable

The task details are:
- Name: {task_name}
- Documentation: {task_documentation}
- Tags: {task_tags}

Format your response as a JSON object with these exact keys: "hook", "context", "value_proposition"
Each value should be a single sentence string.

Example format:
{{
    "hook": "'Our GCE ingress is throwing 502 errors and we're getting flooded with customer complaints' - a common late-night support ticket that no SRE wants to see.",
    "context": "GCE Ingress controllers can sometimes experience issues that aren't immediately visible, leading to potential service disruptions.",
    "value_proposition": "Our automated health check solution helps you proactively identify and resolve ingress issues before they impact your users."
}}"""


def write_intro_paragraph(state: BlogPostState) -> BlogPostState:
    """
    LangGraph node that writes an introduction paragraph for the blog post.

    Args:
        state: The current state of the blog post generation workflow

    Returns:
        BlogPostState: The updated state with the introduction paragraph
    """
    task = state["task"]
    scenario = Scenario(task_name=task.name, task_documentation=task.documentation, task_tags=task.tags)

    # Format the human prompt with task details
    human_prompt = HUMAN_PROMPT_TEMPLATE.format(
        task_name=scenario.task_name,
        task_documentation=scenario.task_documentation,
        task_tags=", ".join(scenario.task_tags),
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    try:
        llm = initialize_llm()
        response = llm.invoke(messages)

        # Try to parse the response content as JSON
        response_dict = json.loads(response.content)

        # Create IntroResponse from the parsed dictionary
        intro_response = IntroResponse.from_dict(response_dict)

        # Initialize raw_paragraphs if needed
        if "raw_paragraphs" not in state:
            state["raw_paragraphs"] = []

        # Create and add the blog paragraph
        body = f"{intro_response.hook} {intro_response.context} {intro_response.value_proposition}"
        intro_paragraph = BlogParagraph(paragraph_type=PARAGRAPH_TYPE_INTRO, header="Overview", body=body)
        state["raw_paragraphs"].append(intro_paragraph)

        return state

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response content was: {response.content}")
        return state
    except KeyError as e:
        print(f"Missing required key in response: {e}")
        print(f"Response dictionary was: {response_dict}")
        return state
    except Exception as e:
        print(f"Unexpected error: {e}")
        return state


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
    print(f"{'='*80}\n")

    # Create initial state
    initial_state: BlogPostState = {
        "task": task,
        "title": task.name.replace("${", "\\${").replace("}", "\\}"),
        "slug": "",  # Not needed for testing
        "blog_post": "",
        "raw_paragraphs": [],
    }

    try:
        # Generate the introduction
        result = write_intro_paragraph(initial_state)

        if result["raw_paragraphs"]:
            # Print the introduction
            print("\nSuccessfully generated intro paragraph:")
            for paragraph in result["raw_paragraphs"]:
                print(f"\n{paragraph.header}: {paragraph.body}")
        else:
            print("\nFailed to generate intro paragraph")

    except Exception as e:
        print(f"\nError processing task: {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            print(f"Caused by: {e.__cause__}")

    print("\nTest completed.")
