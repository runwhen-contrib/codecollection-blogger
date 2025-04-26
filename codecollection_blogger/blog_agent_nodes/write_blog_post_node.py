from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from codecollection_blogger.types import BlogPostState
from codecollection_blogger.blog_agent_nodes.llm import initialize_llm


def write_blog_post(state: BlogPostState) -> BlogPostState:
    """
    Write the main content of the blog post.

    Args:
        state: The current state of the blog post generation workflow

    Returns:
        BlogPostState: The updated state with the blog post content
    """
    # For now, we'll just use the format_blog_post functionality
    # This can be enhanced later to generate more detailed content
    return state
