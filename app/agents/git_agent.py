"""
Git Strategy Agent

Proposes Git branching strategy, repository structure, and generates basic/probable
repo files (README, .gitignore, main entry, config) using LLM. Supports language
and framework (e.g. Python/FastAPI, Node/Express, Java/Spring).
"""

from app.utils.langchain_watsonx import call_llm_structured
from app.models.schemas import GitStrategyOutput


SYSTEM_PROMPT = """You are a Git strategy and repository governance agent.

Your task:
1. Propose a safe, descriptive Git branch name (e.g. feature/db-schema, feature/init-backend)
2. Suggest the repository folder structure for the given LANGUAGE and FRAMEWORK
3. Generate basic/probable files that every project in that language should have

REQUIRED FILES TO GENERATE (with real content):
- README.md: Short project description, how to run, tech stack (use the project description from context)
- .gitignore: Standard ignores for the LANGUAGE (e.g. for Python: __pycache__, .env, venv, *.pyc)
- One main/entry file: e.g. main.py for Python, index.js for Node, src/main.java for Java
- Dependency file: requirements.txt (Python), package.json (Node), pom.xml/build.gradle (Java) - with minimal placeholder content
- Config or app entry if relevant: e.g. config/settings.py, app/__init__.py for Python

RULES:
- Use the exact LANGUAGE and FRAMEWORK from the user context (e.g. python, fastapi OR node, express OR java, spring-boot)
- repository_structure: list of paths that should exist (e.g. ["src/", "tests/", "README.md", ".gitignore"])
- files: list of objects with "path" and "content". Provide ACTUAL file content, not placeholders like "add content here". Keep each file concise but valid.
- Branch name: lowercase, kebab-case (e.g. feature/init-backend)
- base_branch: usually "main"
- For Python: include venv, __pycache__, .env in .gitignore; README with pip install -r requirements.txt
- For Node: include node_modules, .env in .gitignore; README with npm install
- For Java: include target/, .class in .gitignore; README with mvn install or gradle build
- Do NOT generate long boilerplate; keep file content minimal but runnable/valid."""


def propose_git_strategy(project_context: dict) -> GitStrategyOutput:
    """
    Proposes a Git branching strategy, repo structure, and basic repo files.
    
    Args:
        project_context: Dict with:
            - type: "backend" (or "frontend"/"fullstack")
            - framework: "fastapi", "django", "express", "spring-boot", etc.
            - language: "python", "node", "java", "go", etc.
            - description: Optional project description (used in README)
    
    Returns:
        GitStrategyOutput: branch_name, base_branch, repository_structure, action, files (path + content)
    """
    print("🌿 Git Strategy Agent running")
    
    import json
    context_json = json.dumps(project_context, indent=2)
    
    result = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=context_json,
        output_schema=GitStrategyOutput,
        temperature=0.2,
        max_tokens=4096  # Larger to allow file contents
    )
    
    return result


# For standalone testing
if __name__ == "__main__":
    project_context = {
        "type": "backend",
        "framework": "fastapi",
        "language": "python",
        "description": "SaaS platform with user management and organizations"
    }

    result = propose_git_strategy(project_context)
    
    print("\n🌿 GIT STRATEGY OUTPUT:")
    print(f"Branch Name: {result.branch_name}")
    print(f"Base Branch: {result.base_branch}")
    print(f"Action: {result.action}")
    print(f"\n📁 Repository Structure:")
    for path in result.repository_structure:
        print(f"  - {path}")
    print(f"\n📄 Files ({len(result.files)}):")
    for f in result.files:
        print(f"  - {f.path} ({len(f.content)} chars)")
