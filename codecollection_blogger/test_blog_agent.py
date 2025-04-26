import os
import tempfile
from pathlib import Path

from codecollection_blogger.fetch_codecollection import TaskSourceCode
from codecollection_blogger.blog_agent import create_task_blog_post_from_task_source_code


def test_create_task_blog_post():
    """Test creating a blog post from a TaskSourceCode object."""
    # Create a sample TaskSourceCode object
    task = TaskSourceCode(
        name="Test Task",
        tags=["test", "example"],
        documentation="This is a test task for creating blog posts.",
        source_code="""*** Test Case ***
Test Task
    [Documentation]    This is a test task for creating blog posts.
    [Tags]    test    example
    Log    Hello, world!
    Log    This is a test task.
""",
        supporting_files_url="https://github.com/example/repo/tree/main/codebundles/test-task",
    )

    # Create a temporary directory for the output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the blog post
        blog_post = create_task_blog_post_from_task_source_code(task, output_dir=temp_dir)

        # Check that the blog post was created
        output_files = os.listdir(temp_dir)
        assert len(output_files) == 1, f"Expected 1 output file, got {len(output_files)}"

        # Check the content of the blog post
        output_path = os.path.join(temp_dir, output_files[0])
        with open(output_path, "r") as f:
            content = f.read()

        # Check that the content contains the task name, tags, documentation, and source code
        assert "Test Task" in content, "Blog post should contain the task name"
        assert "test" in content and "example" in content, "Blog post should contain the task tags"
        assert (
            "This is a test task for creating blog posts" in content
        ), "Blog post should contain the task documentation"
        assert "Log    Hello, world!" in content, "Blog post should contain the task source code"
        assert (
            "https://github.com/example/repo/tree/main/codebundles/test-task" in content
        ), "Blog post should contain the supporting files URL"

        print(f"Blog post created successfully at {output_path}")
        print("Blog post content:")
        print("-" * 80)
        print(content)
        print("-" * 80)


if __name__ == "__main__":
    test_create_task_blog_post()
