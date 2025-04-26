from typing import Dict, List, Optional
from dataclasses import dataclass
import json

from langchain_core.messages import HumanMessage, SystemMessage

from codecollection_blogger.types import BlogPostState, BlogParagraph, PARAGRAPH_TYPE_ISSUE
from codecollection_blogger.fetch_codecollection import TaskSourceCode
from codecollection_blogger.blog_agent_nodes.llm import initialize_llm


@dataclass
class ATCExample:
    atc_overview: str
    alert: str
    alert_example: str
    ticket: str
    ticket_example: str
    chat: str
    chat_example: str

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ATCExample":
        return cls(
            atc_overview=data["atc_overview"],
            alert=data["alert_description"],
            alert_example=data["alert_example"],
            ticket=data["ticket_description"],
            ticket_example=data["ticket_example"],
            chat=data["chat_description"],
            chat_example=data["chat_example"],
        )


# System prompt for the LLM
SYSTEM_PROMPT = (
    """You are an experienced SRE describing real-world scenarios where Kubernetes automation tasks are valuable."""
)

# Human prompt template
HUMAN_PROMPT_TEMPLATE = """Analyze this Kubernetes automation task and describe scenarios where it would be valuable:

Task Name: {task_name}
Task Documentation: {task_documentation}
Task Tags: {task_tags}

Provide descriptions and examples for three types of scenarios where this automation would be helpful:
1. Datadog alerts that might trigger
2. Support tickets that might be filed
3. Slack conversations in operational channels

Format your response as a JSON object with these exact keys:
- "atc_overview": A technical overview (1-2 sentences) that demonstrates deep SRE expertise. Reference specific monitoring metrics, infrastructure components, failure modes, and operational impact. Use precise technical terminology and explain how this automation fits into a broader observability and incident response strategy.
- "alert_description": A description of relevant Datadog alert types
- "alert_example": A specific example alert message
- "ticket_description": A description of relevant support ticket types
- "ticket_example": A specific example ticket title and description
- "chat_description": A description of relevant Slack conversations
- "chat_example": A specific example chat message thread

Example format:
{{
    "atc_overview": "This automation addresses a critical observability gap in GCP's load balancer infrastructure by proactively monitoring backend service health metrics (loadBalancing.googleapis.com/https/backend_latencies) and ingress controller events. It's particularly valuable during rolling deployments or network policy changes when backend health check failures can cascade into customer-facing 5xx errors, providing early detection before traditional endpoint monitoring would trigger.",
    "alert_description": "High latency alerts from GCE load balancers, particularly focusing on 5xx errors and backend health check failures",
    "alert_example": "[ALERT] High rate of 502 Bad Gateway responses (>5%) detected for ingress frontend-prod-ingress in last 5 minutes",
    "ticket_description": "Urgent tickets about service unavailability or intermittent errors in production services exposed via GCE ingress",
    "ticket_example": "URGENT: Production API returning 502 errors - Multiple customers affected\\nCustomers reporting intermittent API failures. Initial investigation shows potential ingress health check issues.",
    "chat_description": "DevOps channel discussions about service health and customer-impacting issues",
    "chat_example": "@sre-team seeing elevated error rates on the checkout API. Health checks failing for multiple backends. Anyone available to investigate?"
}}"""


def write_atc_paragraph(state: BlogPostState) -> BlogPostState:
    """
    Write a paragraph describing Alert, Ticket, and Chat scenarios where this automation is valuable.

    Args:
        state: The current state of the blog post generation workflow

    Returns:
        BlogPostState: The updated state with the ATC paragraph added
    """
    task = state["task"]

    # Format the human prompt with task details
    human_prompt = HUMAN_PROMPT_TEMPLATE.format(
        task_name=task.name,
        task_documentation=task.documentation,
        task_tags=", ".join(task.tags),
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    try:
        llm = initialize_llm(response_format="json_object")
        response = llm.invoke(messages)

        # Parse the response content as JSON
        response_dict = json.loads(response.content)
        atc_example = ATCExample.from_dict(response_dict)

        # Initialize raw_paragraphs if needed
        if "raw_paragraphs" not in state:
            state["raw_paragraphs"] = []

        # Add the overview paragraph
        overview_paragraph = BlogParagraph(
            paragraph_type=PARAGRAPH_TYPE_ISSUE, header="Operational Context", body=atc_example.atc_overview
        )
        state["raw_paragraphs"].append(overview_paragraph)

        # Create markdown table
        table = [
            "| Scenario | Description | Example |",
            "|----------|-------------|---------|",
            f"| 🔔 Alerts | {atc_example.alert} | {atc_example.alert_example} |",
            f"| 🎫 Tickets | {atc_example.ticket} | {atc_example.ticket_example} |",
            f"| 💬 Chat | {atc_example.chat} | {atc_example.chat_example} |",
        ]

        # Join table rows with newlines
        table_content = "\n".join(table)

        # Create and add the scenarios paragraph
        scenarios_paragraph = BlogParagraph(
            paragraph_type=PARAGRAPH_TYPE_ISSUE, header="Common Scenarios", body=table_content
        )
        state["raw_paragraphs"].append(scenarios_paragraph)

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
        # Generate the ATC paragraph
        result = write_atc_paragraph(initial_state)

        if result["raw_paragraphs"]:
            print("\nSuccessfully generated ATC paragraph:")
            for paragraph in result["raw_paragraphs"]:
                print(f"\n{paragraph.header}:")
                print(paragraph.body)
        else:
            print("\nFailed to generate ATC paragraph")

    except Exception as e:
        print(f"\nError processing task: {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            print(f"Caused by: {e.__cause__}")

    print("\nTest completed.")
