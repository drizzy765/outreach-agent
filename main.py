import asyncio
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from database.connection import init_db
from workflow.graph import run_autonomous_outreach_pipeline
from tools.email_verifier import EmailVerifier, generate_email_permutations
from agents.discovery import ProspectDiscoveryAgent
from agents.audit import TechnicalAuditAgent
from agents.enrichment import LeadEnrichmentAgent
from agents.negotiation import NegotiationEngineAgent

app = typer.Typer(help="Autonomous Multi-Agent Outreach Engine CLI")
console = Console()

@app.command()
def init():
    """Initialize PostgreSQL CRM database tables."""
    console.print("[bold green]Initializing database tables...[/bold green]")
    asyncio.run(init_db())
    console.print("[bold green]✓ Database initialized successfully.[/bold green]")

@app.command()
def run(
    url: str = typer.Option(..., "--url", "-u", help="Target website URL"),
    name: str = typer.Option(..., "--name", "-n", help="Target company name"),
    reply: str = typer.Option(None, "--reply", "-r", help="Simulate an incoming reply from prospect")
):
    """Execute end-to-end multi-agent pipeline for a prospect."""
    console.print(Panel(f"🚀 Running Autonomous Outreach Pipeline for [bold cyan]{name}[/bold cyan] ({url})", style="bold blue"))
    
    # Initialize DB schema if needed
    asyncio.run(init_db())
    
    # Run LangGraph pipeline
    result = asyncio.run(run_autonomous_outreach_pipeline(target_url=url, company_name=name, incoming_reply=reply))

    # Print Results Table
    table = Table(title="Pipeline Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Agent / Phase", style="cyan")
    table.add_column("Result / Finding", style="green")

    table.add_row("1. Discovery", f"Registered {result.get('company_name')} (ID: {result.get('company_id')})")
    audit = result.get('audit_findings', {})
    table.add_row("2. Audit Diagnostics", f"TTFB: {audit.get('ttfb_ms')}ms | Search Gap: {audit.get('search_gap_detected')}")
    table.add_row("3. Lead Enrichment", f"{result.get('primary_lead_name')} ({result.get('primary_lead_email')})")
    table.add_row("4. Value-Add Pitch", f"Angle: {result.get('pitch_angle')} | Subject: {result.get('pitch_subject')}")
    table.add_row("5. Negotiation Stage", f"{result.get('negotiation_stage')}")
    if result.get('human_override_required'):
        table.add_row("⚠️ HITL Handover", f"REASON: {result.get('override_reason')}", style="bold red")

    console.print(table)

    console.print("\n[bold yellow]Drafted Pitch Preview:[/bold yellow]")
    console.print(Panel(result.get("pitch_body", "No pitch drafted"), title=result.get("pitch_subject", "Subject")))

    if result.get("negotiation_response"):
        console.print("\n[bold green]Negotiation Follow-Up Response:[/bold green]")
        console.print(Panel(result.get("negotiation_response"), style="green"))

@app.command()
def verify_email(
    first: str = typer.Argument(..., help="First name"),
    last: str = typer.Argument(..., help="Last name"),
    domain: str = typer.Argument(..., help="Domain (e.g., example.com)")
):
    """Generate permutations and test deliverability using MX & SMTP ping."""
    console.print(f"[bold blue]Testing email permutations for {first} {last} @ {domain}...[/bold blue]")
    perms = generate_email_permutations(first, last, domain)
    verifier = EmailVerifier()

    table = Table(title=f"Email Verification for {domain}", show_header=True, header_style="bold blue")
    table.add_column("Permutation", style="cyan")
    table.add_column("Deliverability Status", style="green")
    table.add_column("Details", style="dim")

    for p in perms[:5]:
        res = verifier.verify(p)
        table.add_row(res["email"], res["status"], str(res.get("details", "")))

@app.command()
def discover(
    source: str = typer.Option("all", "--source", "-s", help="Source to scrape: all, producthunt, hackernews, ycombinator, github"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of prospects to fetch per source"),
    register: bool = typer.Option(False, "--register", "-r", help="Save discovered prospects directly into PostgreSQL CRM")
):
    """Discover new startups and SaaS platforms across multiple channels."""
    console.print(f"[bold cyan]🔍 Discovering prospects from: [magenta]{source}[/magenta] (Limit: {limit})...[/bold cyan]")
    agent = ProspectDiscoveryAgent()

    async def _run_discovery():
        if source == "all":
            results = await agent.discover_multi_source(limit_per_source=limit)
        elif source == "producthunt":
            results = await agent.discover_from_producthunt_rss(limit=limit)
        elif source == "hackernews":
            results = await agent.discover_from_hackernews(limit=limit)
        elif source == "ycombinator":
            results = await agent.discover_from_ycombinator(limit=limit)
        elif source == "github":
            results = await agent.discover_from_github(limit=limit)
        else:
            console.print(f"[red]Unknown source: {source}[/red]")
            return []

        if register and results:
            await init_db()
            saved = await agent.register_prospects(results)
            console.print(f"[green]✓ Successfully registered {len(saved)} companies to PostgreSQL CRM.[/green]")

        return results

    prospects = asyncio.run(_run_discovery())

    table = Table(title="Discovered Prospects", show_header=True, header_style="bold green")
    table.add_column("Company", style="bold cyan")
    table.add_column("Source", style="yellow")
    table.add_column("Website URL", style="blue")
    table.add_column("Industry / Focus", style="dim")

    for p in prospects:
        table.add_row(
            p.get("company_name", "Unknown"),
            p.get("source", "feed"),
            p.get("website_url", ""),
            p.get("industry", "")[:40]
        )

    console.print(table)

@app.command()
def audit(
    url: str = typer.Option(..., "--url", "-u", help="Target website URL to run diagnostics on"),
    playwright: bool = typer.Option(True, "--playwright/--no-playwright", help="Enable Playwright deep headless inspection")
):
    """Run non-invasive technical audit and gap analysis on a target company."""
    console.print(Panel(f"🔬 Running Technical & Performance Audit on [bold cyan]{url}[/bold cyan]", style="bold blue"))
    agent = TechnicalAuditAgent(enable_playwright=playwright)
    findings = asyncio.run(agent.perform_audit(url))

    table = Table(title=f"Diagnostic Findings for {url}", show_header=True, header_style="bold magenta")
    table.add_column("Metric / Check", style="cyan")
    table.add_column("Value / Status", style="green")

    table.add_row("Diagnostic Engine", findings.get("diagnostic_engine", "N/A"))
    table.add_row("HTTP Status Code", str(findings.get("status_code", 200)))
    table.add_row("Load Time / TTFB", f"{findings.get('load_time_ms', 0)}ms / {findings.get('ttfb_ms', 0)}ms")
    table.add_row("Page Weight", f"{findings.get('page_weight_kb', 0)} KB")
    table.add_row("Vector Search Gap Detected", str(findings.get("search_gap_detected", False)))
    table.add_row("Search Diagnosis", findings.get("search_diagnosis", ""))
    table.add_row("AI Voice/Copilot Gap Detected", str(findings.get("ai_agent_gap_detected", False)))
    table.add_row("AI Diagnosis", findings.get("ai_agent_diagnosis", ""))
    table.add_row("JS Console Errors", str(len(findings.get("js_console_errors", []))))
    table.add_row("Detected APIs", ", ".join(findings.get("detected_apis", [])) or "None detected")
    table.add_row("Recommended Pitch Angle", findings.get("recommended_pitch_angle", "CUSTOM_ML_AUDIT"), style="bold yellow")

    console.print(table)
    console.print("\n[bold cyan]Audit Summary:[/bold cyan]")
    console.print(Panel(findings.get("audit_summary", "No summary generated."), style="dim"))

@app.command()
def enrich(
    url: str = typer.Option(..., "--url", "-u", help="Target company website URL to crawl and enrich"),
    save: bool = typer.Option(False, "--save", "-s", help="Save discovered leads to PostgreSQL CRM database")
):
    """Deep crawl website, extract executives and contacts, generate permutations and verify email deliverability."""
    console.print(Panel(f"🎯 Crawling & Enriching Leads for [bold cyan]{url}[/bold cyan]", style="bold magenta"))
    agent = LeadEnrichmentAgent()

    async def _run():
        if save:
            await init_db()
        return await agent.enrich_company(company_id=None, website_url=url)

    leads = asyncio.run(_run())

    table = Table(title=f"Enriched Leads for {url}", show_header=True, header_style="bold green")
    table.add_column("Full Name", style="bold cyan")
    table.add_column("Role", style="yellow")
    table.add_column("Email Address", style="blue")
    table.add_column("Verification Status", style="green")

    for lead in leads:
        table.add_row(
            lead.get("full_name", "Unknown"),
            lead.get("role", "Executive"),
            lead.get("email", ""),
            lead.get("verification_status", "UNVERIFIED")
        )

    console.print(table)

if __name__ == "__main__":
    app()



