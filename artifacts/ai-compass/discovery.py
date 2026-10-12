"""Guided discovery prompts and safe example opportunities."""

DEPARTMENTS = [
    "Finance",
    "HR",
    "Sales",
    "Marketing",
    "Operations",
    "IT",
    "Customer Service",
    "Other",
]

SCALES = ["Individual", "Department", "Organization"]

QUESTIONS = [
    {
        "title": "The outcome",
        "prompt": "What problem would you like to solve, or what outcome would make this process better?",
        "fields": [
            ("business_problem", "Problem or opportunity", "Describe the current friction in a sentence or two."),
            ("desired_outcome", "Desired outcome", "What should become faster, easier, more accurate, or more consistent?"),
        ],
    },
    {
        "title": "The work today",
        "prompt": "Walk through the work as it happens now. Include the repetitive activities and how often they occur.",
        "fields": [
            ("activities", "Daily activities or current process", "What are the main steps people take today?"),
            ("manual_work", "Manual or repetitive work", "Which steps take repeated copying, checking, sorting, or writing?"),
            ("frequency", "How often does this happen?", "For example: several times a day, weekly, or at month-end."),
        ],
    },
    {
        "title": "Tools and information",
        "prompt": "What systems and information are involved? Use fictional or authorized non-sensitive examples only.",
        "fields": [
            ("tools", "Existing business tools and systems", "For example: spreadsheet, CRM, shared drive, ticketing system."),
            ("data_types", "Data and document types", "For example: structured rows, emails, PDFs, policies, or forms."),
        ],
    },
    {
        "title": "Rules and judgment",
        "prompt": "Which parts follow clear rules, and where do people need to review, approve, or handle exceptions?",
        "fields": [
            ("rules", "Rules and approvals", "What rules, checks, or sign-offs apply?"),
            ("exceptions", "Exceptions and human decisions", "What unusual cases need a person's judgment?"),
        ],
    },
    {
        "title": "Scale and impact",
        "prompt": "Estimate the current effort and the scale you have in mind. Rough estimates are fine.",
        "fields": [
            ("time_spent", "Time spent", "Approximate time per person or team, and how often."),
            ("business_impact", "Business impact", "What changes if this gets better? Avoid confidential metrics."),
        ],
    },
    {
        "title": "Readiness and safeguards",
        "prompt": "Think about the intended rollout, data sensitivity, and what still needs to be confirmed.",
        "fields": [
            ("security_concerns", "Security and data sensitivity", "Use broad categories only; do not enter confidential or personal information."),
            ("constraints", "Constraints or missing details", "What would need to be checked before a pilot?"),
        ],
    },
]

OPPORTUNITY_LIBRARY = {
    "Finance": [
        ("Invoice exception triage", "Route invoices that do not match expected fields for a person to review."),
        ("Monthly close checklist", "Track recurring close tasks and flag missing inputs."),
        ("Policy and procedure lookup", "Help staff find answers in approved finance guidance."),
    ],
    "HR": [
        ("Policy question assistant", "Help employees find answers in approved HR policies."),
        ("Interview scheduling coordination", "Reduce back-and-forth while keeping hiring decisions with people."),
        ("Onboarding task tracking", "Coordinate standard onboarding steps and highlight missing items."),
    ],
    "Sales": [
        ("Meeting preparation brief", "Summarize approved account notes into a consistent prep outline."),
        ("CRM hygiene review", "Identify incomplete or inconsistent CRM fields for a salesperson to verify."),
        ("Proposal first draft", "Create a reviewable draft from approved product and customer inputs."),
    ],
    "Marketing": [
        ("Campaign performance summary", "Turn campaign metrics into a repeatable summary for review."),
        ("Content adaptation", "Create channel-specific drafts from approved source content."),
        ("Brand guidance lookup", "Answer questions using approved brand guidance and examples."),
    ],
    "Operations": [
        ("Work instruction lookup", "Help staff find the right step in approved procedures."),
        ("Request intake triage", "Sort incoming requests and route uncertain cases to a person."),
        ("Recurring report preparation", "Combine routine inputs into a draft report for validation."),
    ],
    "IT": [
        ("Internal support request triage", "Categorize requests and suggest existing help articles."),
        ("Knowledge base assistant", "Find answers in approved technical documentation."),
        ("Access request checklist", "Check request completeness while leaving authorization to an approver."),
    ],
    "Customer Service": [
        ("Support reply drafting", "Prepare response drafts from approved guidance for agent review."),
        ("Ticket classification", "Suggest categories and routing for incoming support requests."),
        ("Knowledge article lookup", "Find relevant approved help content for a support agent."),
    ],
    "Other": [
        ("Document intake review", "Extract key fields from standard documents for human verification."),
        ("Recurring task coordination", "Track repeatable steps and alert people to missing inputs."),
        ("Internal knowledge lookup", "Find answers in a controlled collection of approved documents."),
    ],
}


def suggested_opportunities(department: str, role: str = "", responsibilities: str = ""):
    """Return three fictional, low-risk starting points for the selected context."""
    opportunities = OPPORTUNITY_LIBRARY.get(department, OPPORTUNITY_LIBRARY["Other"])
    return [
        {
            "title": title,
            "description": description,
            "department": department,
            "role": role.strip(),
            "context": responsibilities.strip(),
        }
        for title, description in opportunities[:3]
    ]

