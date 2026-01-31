"""
GitHub Push Skill - Push proposed repo structure to a real GitHub repository.

Uses PyGithub with the user's Personal Access Token (PAT).
For use with watsonx Orchestrate: host this app and call POST /git/push with token.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def push_repo_structure_to_github(
    github_token: str,
    repo_full_name: str,
    branch_name: str,
    base_branch: str,
    files: list[dict],
    commit_message_prefix: str = "Add",
    create_repo_if_not_exists: bool = True,
    repo_private: bool = True,
) -> dict[str, Any]:
    """
    Create a branch on GitHub and push all proposed files.
    
    Handles empty repos (no branches) and missing repos (creates them).

    Uses the GitHub API (PyGithub). Token must have repo scope.

    Args:
        github_token: GitHub Personal Access Token (classic) with repo scope.
        repo_full_name: "owner/repo" (e.g. "myorg/my-repo").
        branch_name: Branch to create (e.g. "feature/db-schema").
        base_branch: Branch to create from (e.g. "main"). If empty repo, creates main first.
        files: List of {"path": str, "content": str}.
        commit_message_prefix: Prefix for each file commit (e.g. "Add README.md").
        create_repo_if_not_exists: If True, creates the repo when not found (requires repo permission).
        repo_private: If creating repo, whether it should be private.

    Returns:
        Dict with status, url, files_created, error (if any).
    """
    try:
        from github import Github, GithubException
    except ImportError:
        return {
            "success": False,
            "error": "PyGithub not installed. Run: pip install PyGithub",
            "repository": repo_full_name,
            "branch": branch_name,
        }

    if not github_token or not github_token.strip():
        return {
            "success": False,
            "error": "GitHub token is required",
            "repository": repo_full_name,
            "branch": branch_name,
        }

    if not files:
        return {
            "success": False,
            "error": "No files to push",
            "repository": repo_full_name,
            "branch": branch_name,
        }

    try:
        g = Github(github_token)
        
        # Try to get repo; if not found, create it
        try:
            repo = g.get_repo(repo_full_name)
        except GithubException as e:
            if e.status == 404 and create_repo_if_not_exists:
                # Repo doesn't exist - create it
                parts = repo_full_name.split("/")
                if len(parts) != 2:
                    return {
                        "success": False,
                        "error": f"Invalid repo format: {repo_full_name}. Use owner/repo.",
                        "repository": repo_full_name,
                        "branch": branch_name,
                    }
                owner_name, repo_name = parts
                try:
                    user = g.get_user()
                    if user.login == owner_name:
                        # User repo
                        repo = user.create_repo(
                            name=repo_name,
                            private=repo_private,
                            auto_init=False,  # We'll add files ourselves
                        )
                    else:
                        # Org repo
                        org = g.get_organization(owner_name)
                        repo = org.create_repo(
                            name=repo_name,
                            private=repo_private,
                            auto_init=False,
                        )
                    logger.info("Created repo: %s", repo_full_name)
                except Exception as create_err:
                    return {
                        "success": False,
                        "error": f"Repo not found and failed to create: {create_err!s}",
                        "repository": repo_full_name,
                        "branch": branch_name,
                    }
            else:
                return {
                    "success": False,
                    "error": f"Repo not found: {e!s}",
                    "repository": repo_full_name,
                    "branch": branch_name,
                }

        # Check if repo is empty (no branches)
        base_sha = None
        repo_is_empty = False
        try:
            base_ref = repo.get_branch(base_branch)
            base_sha = base_ref.commit.sha
        except GithubException as e:
            if e.status == 404:
                # Branch not found - try default branch
                try:
                    default_branch = repo.default_branch
                    base_ref = repo.get_branch(default_branch)
                    base_sha = base_ref.commit.sha
                except Exception:
                    # Repo is completely empty - no branches at all
                    repo_is_empty = True
                    logger.info("Repo %s is empty (no branches); will create first commit", repo_full_name)
            else:
                return {
                    "success": False,
                    "error": f"Error accessing branch: {e!s}",
                    "repository": repo_full_name,
                    "branch": branch_name,
                }

        # Handle empty repo: create first file to establish the branch
        if repo_is_empty:
            # For empty repo, we can't create a ref without a commit. So we create files directly on branch_name.
            # PyGithub create_file will create the branch if it doesn't exist (when repo is empty).
            files_created: list[str] = []
            for i, f in enumerate(files):
                path = f.get("path") or ""
                content = f.get("content") or ""
                if not path:
                    continue
                try:
                    if i == 0:
                        # First file: creates the branch
                        repo.create_file(
                            path,
                            f"Initial commit: {commit_message_prefix} {path}",
                            content,
                            branch=branch_name,
                        )
                    else:
                        # Subsequent files: add to existing branch
                        repo.create_file(
                            path,
                            f"{commit_message_prefix} {path}",
                            content,
                            branch=branch_name,
                        )
                    files_created.append(path)
                except Exception as e:
                    logger.warning("Create file %s in empty repo failed: %s", path, e)
            
            url = f"https://github.com/{repo_full_name}/tree/{branch_name}"
            return {
                "success": True,
                "repository": repo_full_name,
                "branch": branch_name,
                "base_branch": base_branch,
                "url": url,
                "files_created": files_created,
                "files_count": len(files_created),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "created_repo": True if "created" in locals() else False,
                "empty_repo": True,
            }

        # Create new branch (ref) pointing at base commit
        ref_name = f"refs/heads/{branch_name}"
        try:
            repo.create_git_ref(ref_name, base_sha)
        except GithubException as e:
            if e.status == 422 and "Reference already exists" in str(e):
                # Branch exists; we'll add/update files on it
                pass
            else:
                return {
                    "success": False,
                    "error": f"Failed to create branch: {e!s}",
                    "repository": repo_full_name,
                    "branch": branch_name,
                }

        # Push each file (each create_file creates a commit on the branch)
        files_created = []
        for f in files:
            path = f.get("path") or ""
            content = f.get("content") or ""
            if not path:
                continue
            try:
                repo.create_file(
                    path,
                    f"{commit_message_prefix} {path}",
                    content,
                    branch=branch_name,
                )
                files_created.append(path)
            except GithubException as e:
                if e.status == 422 and "already exists" in str(e).lower():
                    try:
                        # Update existing file: need blob sha
                        contents = repo.get_contents(path, ref=branch_name)
                        repo.update_file(
                            path,
                            f"Update {path}",
                            content,
                            contents.sha,
                            branch=branch_name,
                        )
                        files_created.append(path)
                    except Exception as e2:
                        logger.warning("Update file %s failed: %s", path, e2)
                        # Continue with other files
                else:
                    logger.warning("Create file %s failed: %s", path, e)

        url = f"https://github.com/{repo_full_name}/tree/{branch_name}"
        return {
            "success": True,
            "repository": repo_full_name,
            "branch": branch_name,
            "base_branch": base_branch,
            "url": url,
            "files_created": files_created,
            "files_count": len(files_created),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception("GitHub push failed")
        return {
            "success": False,
            "error": str(e),
            "repository": repo_full_name,
            "branch": branch_name,
        }
