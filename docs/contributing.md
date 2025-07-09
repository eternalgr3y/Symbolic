# Contributing to SymbolicAGI

Thank you for your interest in contributing! We welcome improvements, bug fixes, and new features. To ensure a smooth and collaborative process, please follow these guidelines.

## Development Setup

1.  **Fork & Clone:** Fork the repository on GitHub and clone your fork locally.
2.  **Create a Virtual Environment:** We strongly recommend using a virtual environment to manage dependencies.
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install in Editable Mode:** Install the package in "editable" mode with the `[dev]` extras. This will install all core dependencies plus the tools needed for formatting, linting, and type checking.
    ```bash
    pip install -e ".[dev]"
    ```
4.  **Set up Pre-Commit Hooks (Optional but Recommended):** This will automatically run formatters and linters before you commit, ensuring your contributions match the project's style.
    ```bash
    pre-commit install
    ```

## Code Style and Quality

-   **Formatting:** We use `black` for code formatting and `isort` for import sorting. The `pyproject.toml` file contains the configuration for these tools. If you use the pre-commit hooks, this will be handled automatically.
-   **Linting:** We use `ruff` for fast, comprehensive linting.
-   **Type Checking:** The project uses strict type hints and is checked with `mypy`. All new code must include explicit type annotations and pass `mypy` checks.

You can run all checks manually with:
```bash
ruff check .
mypy symbolic_agi

Submitting a Pull Request
Create a New Branch: Create a feature branch from the main branch for your changes.
git checkout -b feature/my-new-feature

Make Your Changes: Implement your feature or bug fix. Remember to add or update documentation and tests as needed.
Run Checks: Ensure all linting and type checks pass before pushing.
Commit and Push: Use a clear and descriptive commit message.
git commit -m "feat: add new tool for weather forecasting"
git push origin feature/my-new-feature

Open a Pull Request: Go to the original repository on GitHub and open a pull request. Provide a clear description of the changes you've made and why.
We look forward to your contributions!