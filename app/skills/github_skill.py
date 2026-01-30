def create_branch(repo_name: str, branch_name: str, base_branch: str = "main"):
    print(f"📂 Creating branch '{branch_name}' from '{base_branch}' in repo '{repo_name}'")

    return {
        "repository": repo_name,
        "branch": branch_name,
        "base_branch": base_branch,
        "status": "created (mock)"
    }
