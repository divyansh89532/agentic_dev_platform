"""
OpenAPI Export Utility for IBM watsonx Orchestrate

This module provides utilities to export your FastAPI endpoints as OpenAPI specs
that can be imported into watsonx Orchestrate as tools/skills.

Usage:
    python -m app.utils.openapi_export

This will generate:
    - openapi_full.json: Complete API spec
    - openapi_agents.json: Just the agent endpoints
    - openapi_skills.json: Just the skill endpoints
"""

import json
from pathlib import Path
from typing import Optional
from fastapi.openapi.utils import get_openapi


def get_app():
    """Import the FastAPI app."""
    from app.main import app
    return app


def generate_openapi_spec(
    title: Optional[str] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
    include_paths: Optional[list[str]] = None,
    exclude_paths: Optional[list[str]] = None
) -> dict:
    """
    Generate OpenAPI spec for the application.
    
    Args:
        title: Override the API title
        description: Override the API description
        version: API version
        include_paths: Only include these path prefixes (e.g., ["/agents"])
        exclude_paths: Exclude these path prefixes (e.g., ["/health"])
    
    Returns:
        OpenAPI spec as a dictionary
    """
    app = get_app()
    
    openapi_schema = get_openapi(
        title=title or app.title,
        version=version,
        description=description or app.description,
        routes=app.routes,
    )
    
    # Filter paths if specified
    if include_paths or exclude_paths:
        filtered_paths = {}
        for path, operations in openapi_schema.get("paths", {}).items():
            # Check include filter
            if include_paths:
                if not any(path.startswith(prefix) for prefix in include_paths):
                    continue
            
            # Check exclude filter
            if exclude_paths:
                if any(path.startswith(prefix) for prefix in exclude_paths):
                    continue
            
            filtered_paths[path] = operations
        
        openapi_schema["paths"] = filtered_paths
    
    return openapi_schema


def export_for_watsonx_orchestrate(output_dir: str = ".") -> dict:
    """
    Export OpenAPI specs optimized for IBM watsonx Orchestrate.
    
    watsonx Orchestrate expects:
    - Valid OpenAPI 3.0+ spec
    - Clear operation IDs
    - Well-defined request/response schemas
    - Proper descriptions for each operation
    
    Args:
        output_dir: Directory to write the exported files
    
    Returns:
        Dictionary with paths to generated files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    generated_files = {}
    
    # 1. Full API spec
    full_spec = generate_openapi_spec(
        title="Agentic Developer Platform API",
        description="AI-powered platform for automating development setup using IBM watsonx.ai",
        exclude_paths=["/health", "/docs", "/redoc", "/openapi.json"]
    )
    
    full_spec_path = output_path / "openapi_full.json"
    with open(full_spec_path, "w") as f:
        json.dump(full_spec, f, indent=2)
    generated_files["full"] = str(full_spec_path)
    
    # 2. Agent endpoints only (LLM-powered)
    agents_spec = generate_openapi_spec(
        title="Agentic Developer Platform - AI Agents",
        description="LLM-powered agents for requirements extraction, database design, review, and git strategy",
        include_paths=["/agents"]
    )
    
    agents_spec_path = output_path / "openapi_agents.json"
    with open(agents_spec_path, "w") as f:
        json.dump(agents_spec, f, indent=2)
    generated_files["agents"] = str(agents_spec_path)
    
    # 3. Skill endpoints only (deterministic)
    skills_spec = generate_openapi_spec(
        title="Agentic Developer Platform - Skills",
        description="Deterministic skills for validation and other operations",
        include_paths=["/skills"]
    )
    
    skills_spec_path = output_path / "openapi_skills.json"
    with open(skills_spec_path, "w") as f:
        json.dump(skills_spec, f, indent=2)
    generated_files["skills"] = str(skills_spec_path)
    
    # 4. Orchestration endpoint only (main workflow)
    orchestrate_spec = generate_openapi_spec(
        title="Agentic Developer Platform - Orchestration",
        description="Main orchestration endpoint that runs the complete development setup pipeline",
        include_paths=["/orchestrate"]
    )
    
    orchestrate_spec_path = output_path / "openapi_orchestrate.json"
    with open(orchestrate_spec_path, "w") as f:
        json.dump(orchestrate_spec, f, indent=2)
    generated_files["orchestrate"] = str(orchestrate_spec_path)
    
    return generated_files


def print_watsonx_import_instructions():
    """Print instructions for importing into watsonx Orchestrate."""
    instructions = """
╔══════════════════════════════════════════════════════════════════════════════╗
║           IMPORTING INTO IBM WATSONX ORCHESTRATE                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  1. Deploy your FastAPI app to a public endpoint (e.g., IBM Code Engine)    ║
║                                                                              ║
║  2. Go to watsonx Orchestrate → Skills → Add Skill → Import from OpenAPI    ║
║                                                                              ║
║  3. Upload one of the generated OpenAPI JSON files:                         ║
║     - openapi_full.json      → All endpoints                                ║
║     - openapi_agents.json    → Just AI agent endpoints                      ║
║     - openapi_skills.json    → Just deterministic skill endpoints           ║
║     - openapi_orchestrate.json → Main orchestration endpoint                ║
║                                                                              ║
║  4. Configure authentication if needed (API key header, etc.)               ║
║                                                                              ║
║  5. Test the imported skill in watsonx Orchestrate                          ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TIP: For hackathon demos, import openapi_orchestrate.json for the main     ║
║       workflow, then add individual agents for more granular control.       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(instructions)


if __name__ == "__main__":
    print("\n🔧 Exporting OpenAPI specs for IBM watsonx Orchestrate...\n")
    
    files = export_for_watsonx_orchestrate(output_dir="./openapi_exports")
    
    print("✅ Generated OpenAPI specs:")
    for spec_type, path in files.items():
        print(f"   - {spec_type}: {path}")
    
    print_watsonx_import_instructions()
