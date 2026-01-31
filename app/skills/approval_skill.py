"""
Approval Skill - Human-in-the-loop approval workflow.

In production, this could integrate with:
- Slack (approval buttons)
- Web UI (approval dashboard)
- ServiceNow (ITSM tickets)
- Email (approval links)
"""

from datetime import datetime, timezone
from typing import Optional


def request_approval(context: dict) -> dict:
    """
    Request human approval for a database design.
    
    This is a simulated approval skill. In production, this would:
    1. Send notification to approvers
    2. Wait for approval response
    3. Return the decision
    
    Args:
        context: Dictionary containing:
            - review: The review output that triggered approval
            - db_design: The database design being approved
    
    Returns:
        Dictionary with approval decision:
            - approved: bool
            - approved_by: str (username/email)
            - timestamp: ISO timestamp
            - comments: Optional reviewer comments
    """
    print("🧑‍⚖️ Approval requested with context:")
    
    # Log key info for visibility
    if "review" in context:
        review = context["review"]
        risk_level = review.get("risk_level", "UNKNOWN")
        issues = review.get("issues", [])
        print(f"   Risk Level: {risk_level}")
        print(f"   Issues: {len(issues)}")
    
    # In production, this would block until human responds
    # For hackathon demo, auto-approve
    return {
        "approved": True,
        "approved_by": "demo-user@example.com",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comments": "Auto-approved for demo purposes"
    }


def request_approval_interactive(
    context: dict,
    timeout_seconds: int = 300
) -> dict:
    """
    Interactive approval request (for CLI/local testing).
    
    Prompts the user in the terminal for approval decision.
    
    Args:
        context: Same as request_approval
        timeout_seconds: How long to wait for response
    
    Returns:
        Same as request_approval
    """
    print("\n" + "="*60)
    print("🧑‍⚖️ APPROVAL REQUIRED")
    print("="*60)
    
    if "review" in context:
        review = context["review"]
        print(f"\n📋 Assessment: {review.get('assessment', 'N/A')}")
        print(f"⚠️  Risk Level: {review.get('risk_level', 'UNKNOWN')}")
        
        issues = review.get("issues", [])
        if issues:
            print(f"\n🔍 Issues Found ({len(issues)}):")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
    
    print("\n" + "-"*60)
    
    try:
        response = input("Approve this design? (y/n): ").strip().lower()
        approved = response in ("y", "yes", "1", "true")
        
        comments: Optional[str] = None
        if not approved:
            comments = input("Reason for rejection (optional): ").strip() or None
        
        return {
            "approved": approved,
            "approved_by": "interactive-user",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "comments": comments
        }
    except (KeyboardInterrupt, EOFError):
        return {
            "approved": False,
            "approved_by": "system",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "comments": "Approval cancelled by user"
        }
