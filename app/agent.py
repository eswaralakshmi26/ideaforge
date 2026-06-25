# ruff: noqa
import os
import re
import json
import logging
from typing import Any, AsyncGenerator
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent
from google.adk.workflow import Workflow, START
from google.adk.tools import AgentTool
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.genai import types

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from app.config import config

# Configure logging
logger = logging.getLogger("ideaforge")
logger.setLevel(logging.INFO)

# Define schemas for input and output
class BusinessIdeaInput(BaseModel):
    idea: str = Field(description="The raw business idea description.")

class ReviewInput(BaseModel):
    feedback: str = Field(description="User feedback on the proposed idea.")

# Local MCP toolset for domain-specific operations
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv",
            args=["run", "python", "app/mcp_server.py"]
        )
    )
)

# 1. Define Specialized Sub-Agents
critic_agent = LlmAgent(
    name="critic_agent",
    model=config.model,
    instruction="""You are a critical business analyst. Analyze the raw business idea and identify:
1. Weaknesses & risks
2. Potential failure points
3. SWOT analysis (Strengths, Weaknesses, Opportunities, Threats)
Provide a clear, structured critical report. Use your competitor analysis and break-even calculation tools where relevant.""",
    description="Analyzes business ideas to identify weaknesses, risks, and SWOT components.",
    tools=[mcp_toolset]
)

strategist_agent = LlmAgent(
    name="strategist_agent",
    model=config.model,
    instruction="""You are a startup growth strategist. Analyze the business idea and identify:
1. Unique features and value propositions
2. Improvements to the original concept
3. Potential business models (monetization strategies)
Provide a clear, structured strategy report. Use your market trends and break-even calculation tools to refine the business model.""",
    description="Suggests improvements, unique features, and business models for business ideas.",
    tools=[mcp_toolset]
)

marketing_agent = LlmAgent(
    name="marketing_agent",
    model=config.model,
    instruction="""You are a branding and marketing expert. Analyze the business idea and identify:
1. Catchy and creative business name ideas
2. Target audience demographics and psychographics
3. Go-to-market channels
Provide a clear, structured branding and marketing report. Use your market trends and brand slogan tools to generate branding assets.""",
    description="Generates catchy names, identifies target audience, and marketing strategies.",
    tools=[mcp_toolset]
)

# 2. Define Lead Orchestrator Agent
orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=config.model,
    instruction="""You are the Lead Startup Incubator Coordinator. Your job is to take a raw business idea and coordinate with specialized sub-agents to refine it.
Raw Idea: {idea}
Previous Feedback (if any): {feedback}

You must execute the following sequence:
1. Delegate the idea to the critic_agent to analyze weaknesses and SWOT.
2. Delegate the idea to the strategist_agent to design unique features and monetization models.
3. Delegate the idea to the marketing_agent to generate catchy names and target audience info.
4. Synthesize all their reports into a single, cohesive, beautiful business proposal.

If previous feedback is provided, adapt and refine the proposal based on it.
""",
    tools=[
        AgentTool(critic_agent),
        AgentTool(strategist_agent),
        AgentTool(marketing_agent)
    ],
    output_key="orchestrator_output"
)

# 3. Define Workflow Nodes
def security_checkpoint(ctx: Context, node_input: Any) -> Event:
    # Robust extraction of the idea string from various input types
    idea_text = ""
    if isinstance(node_input, str):
        idea_text = node_input
    elif hasattr(node_input, 'parts'):
        # Extract text from content parts (handles types.Content from different package loaders)
        idea_text = "".join(part.text for part in node_input.parts if hasattr(part, 'text') and part.text)
    elif isinstance(node_input, dict):
        idea_text = node_input.get("idea", "")
    elif hasattr(node_input, "idea"):
        idea_text = node_input.idea
    else:
        idea_text = str(node_input)

    # If the idea text itself is a JSON string (e.g. sent from playground as JSON), parse it.
    idea_text = idea_text.strip()
    if idea_text.startswith("{") and idea_text.endswith("}"):
        try:
            parsed = json.loads(idea_text)
            if isinstance(parsed, dict) and "idea" in parsed:
                idea_text = parsed["idea"]
        except Exception:
            pass

    audit_data = {
        "event_type": "security_audit",
        "input_length": len(idea_text),
        "severity": "INFO",
        "issues_found": []
    }
    
    # 1. PII Scrubbing
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'\b(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b'
    
    sanitized_idea = idea_text
    if re.search(email_pattern, idea_text):
        sanitized_idea = re.sub(email_pattern, "[REDACTED_EMAIL]", sanitized_idea)
        audit_data["issues_found"].append("email_pii_detected")
        audit_data["severity"] = "WARNING"
        
    if re.search(phone_pattern, idea_text):
        sanitized_idea = re.sub(phone_pattern, "[REDACTED_PHONE]", sanitized_idea)
        audit_data["issues_found"].append("phone_pii_detected")
        audit_data["severity"] = "WARNING"
        
    # 2. Prompt Injection Detection
    injection_keywords = ["ignore previous instructions", "system prompt", "override", "you must now act as", "bypass"]
    found_injection = False
    for kw in injection_keywords:
        if kw in idea_text.lower():
            found_injection = True
            audit_data["issues_found"].append(f"prompt_injection_keyword_detected: {kw}")
            audit_data["severity"] = "CRITICAL"
            break
            
    # 3. Domain Specific Rule: Prohibited business types (e.g. weapons, hacking, drugs)
    prohibited_keywords = ["weapons", "hacking", "illegal", "drugs", "exploit", "malware"]
    found_prohibited = False
    for kw in prohibited_keywords:
        if kw in idea_text.lower():
            found_prohibited = True
            audit_data["issues_found"].append(f"prohibited_business_domain: {kw}")
            audit_data["severity"] = "CRITICAL"
            break
            
    # Log the structured audit event
    logger.info(json.dumps(audit_data))
    
    if found_injection or found_prohibited:
        # Route to security event block
        return Event(output=f"Security violation detected: {', '.join(audit_data['issues_found'])}", route="block")
        
    # Initialize session state keys to avoid KeyErrors
    ctx.state["idea"] = sanitized_idea
    ctx.state["feedback"] = ""
    ctx.state["proposal"] = ""
    
    return Event(output=sanitized_idea, route="pass")

def security_event(ctx: Context, node_input: str):
    error_msg = f"❌ **Security Checkpoint Alert**\n\nYour input was flagged and blocked by our safety filters. Reason: {node_input}."
    yield Event(
        content=types.Content(
            role='model',
            parts=[types.Part.from_text(text=error_msg)]
        )
    )
    yield Event(output=error_msg)

async def human_review(ctx: Context, node_input: Any) -> AsyncGenerator[Event, None]:
    interrupt_id = "user_review"
    
    # Check if the user response is already in the inputs
    if not ctx.resume_inputs or interrupt_id not in ctx.resume_inputs:
        # Save current proposal output to state
        proposal = ""
        if isinstance(node_input, types.Content):
            # Extract text from content
            proposal = "".join(part.text for part in node_input.parts if part.text)
        else:
            proposal = str(node_input)
            
        ctx.state["proposal"] = proposal
        
        # Pause and ask the user for review
        yield RequestInput(
            interrupt_id=interrupt_id,
            message=f"Here is the refined business proposal:\n\n{proposal}\n\nDo you want to refine this idea or approve it? (Reply with 'refine: [your feedback]' or 'approve')"
        )
        return
    
    # Resume with user feedback
    user_response = ctx.resume_inputs[interrupt_id]
    yield Event(output=user_response)

def post_review_processor(ctx: Context, node_input: str) -> Event:
    response = node_input.strip()
    if response.lower() == "approve":
        return Event(output=ctx.state.get("proposal", ""), route="approve")
    elif response.lower().startswith("refine:"):
        feedback = response[7:].strip()
        ctx.state["feedback"] = feedback
        return Event(output=feedback, route="refine")
    else:
        # Treat any other text as refinement feedback
        ctx.state["feedback"] = response
        return Event(output=response, route="refine")

def final_output(ctx: Context, node_input: str):
    text_content = f"🎉 **Business Idea Approved!**\n\nHere is your finalized plan:\n\n{node_input}"
    yield Event(
        content=types.Content(
            role='model',
            parts=[types.Part.from_text(text=text_content)]
        )
    )
    yield Event(output=node_input)

# 4. Construct the Workflow
workflow = Workflow(
    name="ideaforge_workflow",
    edges=[
        ('START', security_checkpoint),
        (security_checkpoint, {"pass": orchestrator_agent, "block": security_event}),
        (orchestrator_agent, human_review),
        (human_review, post_review_processor),
        (post_review_processor, {"refine": orchestrator_agent, "approve": final_output})
    ]
)

# 5. Define App
app = App(
    root_agent=workflow,
    name="app",
    resumability_config=ResumabilityConfig(is_resumable=True)
)

root_agent = workflow

