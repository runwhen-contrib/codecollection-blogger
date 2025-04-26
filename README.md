# Code Collection Blogger

A tool for generating blog posts from tasks in the RunWhen Code Collections. The RunWhen Code Collections are open-source troubleshooting libraries for Kubernetes and cloud infrastructure components, containing CodeBundles that perform health, operational, and troubleshooting tasks. The two main repositories are:

- [RunWhen CLI CodeCollection](https://github.com/runwhen-contrib/rw-cli-codecollection) - A CLI-focused troubleshooting library
- [RunWhen Public CodeCollection](https://github.com/runwhen-contrib/rw-public-codecollection) - A runbook-focused troubleshooting library

## Prerequisites

- Python 3.12 or higher
- [Poetry](https://python-poetry.org/docs/) for dependency management
- Required API tokens (see Configuration section)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/runwhen-contrib/codecollection-blogger
cd codecollection-blogger
```

2. Install dependencies using Poetry:
```bash
poetry install
```

## Configuration

Before running the tool, you need to set up the following environment variables. These can be set by sourcing the `tokens.env` file:

- `GITHUB_PAT`: GitHub Personal Access Token for accessing the code collection repository
- `OPENAI_API_KEY`: OpenAI API key for generating blog content

You can source the tokens file:
```bash
source tokens.env
```

## Usage

1. Activate the Poetry virtual environment:
```bash
poetry shell
```

2. Run the CLI tool with default settings:
```bash
python codecollection_blogger/cli.py
```

### Command Line Options

The tool supports the following command line options:

- `--repo-url`: URL of the code collection repository (default: https://github.com/runwhen-contrib/rw-cli-codecollection)
- `--output-dir`: Directory to save the blog posts (default: blog_posts)
- `--limit`: Maximum number of tasks to generate blog posts for (default: 5)
- `--tag-filter`: Only generate blog posts for tasks with a specific tag

Example with custom options:
```bash
python codecollection_blogger/cli.py --repo-url <your-repo> --output-dir my_posts --limit 10 --tag-filter "tutorial"
```

## Project Structure

- `codecollection_blogger/`: Main package containing the source code
- `blog_posts/`: Default directory for generated blog posts
- `tests/`: Test files
- `tokens.env`: Environment variables for API tokens

## Dependencies

The project uses the following main dependencies:
- robotframework
- langgraph
- langchain-openai
- langchain-core
- dataclasses-json

All dependencies are managed through Poetry and specified in `pyproject.toml`.

## Related Resources

- [RunWhen CLI CodeCollection](https://github.com/runwhen-contrib/rw-cli-codecollection) - The CLI-focused repository containing CodeBundles and tasks
- [RunWhen Public CodeCollection](https://github.com/runwhen-contrib/rw-public-codecollection) - The runbook-focused repository containing CodeBundles and tasks
- [RunWhen Platform](https://registry.runwhen.com) - The platform that utilizes these CodeBundles for infrastructure troubleshooting
