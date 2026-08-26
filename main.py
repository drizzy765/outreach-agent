import asyncio
import logging
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from database.connection import init_db
from workflow.graph import run_autonomous_outreach_pipeline
from workflow.scheduler import AutonomousOutreachScheduler
from tools.email_verifier import EmailVerifier, generate_email_permutations
from tools.email_sender import OutboundEmailSender
from tools.imap_listener import InboundIMAPListener
from agents.discovery import ProspectDiscoveryAgent
from agents.audit import TechnicalAuditAgent
from agents.enrichment import LeadEnrichmentAgent
from agents.pitcher import ValueAddPitcherAgent
from agents.negotiation import NegotiationEngineAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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
    
    async def _execute_pipeline():
        try:
            await init_db()
        except Exception:
            pass
        try:
            return await run_autonomous_outreach_pipeline(target_url=url, company_name=name, incoming_reply=reply)
        finally:
            try:
                from database.connection import engine
                await engine.dispose()
                await asyncio.sleep(0.05)
            except Exception:
                pass

    # Run LangGraph pipeline within single event loop
    result = asyncio.run(_execute_pipeline())

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

@app.command()
def pitch(
    url: str = typer.Option(..., "--url", "-u", help="Target company website URL"),
    name: str = typer.Option(..., "--name", "-n", help="Target company name"),
    lead: str = typer.Option("Founder", "--lead", "-l", help="Lead name (e.g. Alex Mercer)"),
    role: str = typer.Option("CTO", "--role", help="Lead role title (e.g. CTO)"),
    angle: str = typer.Option(None, "--angle", "-a", help="Pitch angle: CUSTOM_ML_AUDIT or QUANTVAULT_DEMO")
):
    """Generate hyper-personalized value-add pitch and tailored architecture blueprint."""
    console.print(Panel(f"✍️ Generating AI Pitch for [bold cyan]{name}[/bold cyan] ({url})", style="bold yellow"))
    
    async def _execute_pitch():
        audit_agent = TechnicalAuditAgent(enable_playwright=False)
        findings = await audit_agent.perform_audit(url)
        pitcher = ValueAddPitcherAgent()
        draft = await pitcher.generate_pitch_async(
            lead_name=lead,
            lead_role=role,
            company_name=name,
            website_url=url,
            audit_findings=findings,
            pitch_angle=angle
        )
        return draft

    draft = asyncio.run(_execute_pitch())

    console.print(f"\n[bold green]Model / Provider Used:[/bold green] [cyan]{draft.get('provider_used')}[/cyan]")
    console.print(f"[bold green]Pitch Angle:[/bold green] [yellow]{draft.get('pitch_type')}[/yellow]")
    console.print(f"[bold green]Subject Line:[/bold green] [bold white]{draft.get('subject')}[/bold white]\n")

    console.print(Panel(draft.get("body", ""), title="Drafted Outreach Body", style="green"))

@app.command()
def send(
    to: str = typer.Option(..., "--to", "-t", help="Recipient email address"),
    subject: str = typer.Option(..., "--subject", "-s", help="Email subject line"),
    body: str = typer.Option(..., "--body", "-b", help="Email body text")
):
    """Send outbound pitch email via authenticated SMTP or test in dry-run mode."""
    sender = OutboundEmailSender()
    console.print(f"[bold cyan]📤 Dispatching outbound email to [green]{to}[/green]...[/bold cyan]")
    res = asyncio.run(sender.send_email(recipient_email=to, subject=subject, body_text=body))

    table = Table(title="Outbound Transmission Status", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Details", style="green")

    table.add_row("Status", res.get("status", "UNKNOWN"))
    table.add_row("Sender Domain", res.get("sender", "N/A"))
    table.add_row("Recipient", res.get("recipient", to))
    table.add_row("Jitter Delay", f"{res.get('jitter_delay_seconds', 0)}s")
    table.add_row("Daily Count", str(res.get("daily_sent_count", 0)))
    table.add_row("Message ID", str(res.get("message_id", "N/A")))
    table.add_row("Details", res.get("details", ""))

    console.print(table)

@app.command()
def inbox(
    mock_sender: Optional[str] = typer.Option(None, "--mock-sender", help="Inject a mock reply sender email"),
    mock_body: Optional[str] = typer.Option(None, "--mock-body", help="Inject a mock reply body text")
):
    """Check IMAP inbox for new prospect replies or simulate incoming responses."""
    listener = InboundIMAPListener()
    if mock_sender and mock_body:
        listener.inject_mock_reply(
            sender=mock_sender,
            subject="Re: Technical audit findings",
            body=mock_body
        )
        console.print(f"[yellow]Simulating incoming reply from {mock_sender}...[/yellow]")

    replies = asyncio.run(listener.check_inbox())

    if not replies:
        console.print("[dim]No new replies found in inbox.[/dim]")
        return

    table = Table(title="Inbound Prospect Replies", show_header=True, header_style="bold green")
    table.add_column("Sender", style="bold cyan")
    table.add_column("Subject", style="yellow")
    table.add_column("Body Snippet", style="dim")
    table.add_column("Source", style="blue")

    for msg in replies:
        table.add_row(
            msg.get("sender", "Unknown"),
            msg.get("subject", "No Subject"),
            msg.get("body", "")[:80] + "...",
            msg.get("source", "imap")
        )

@app.command()
def followup(
    days: int = typer.Option(3, "--days", "-d", help="Days threshold of inactivity to trigger follow-up bump")
):
    """Scan PostgreSQL CRM for stale outreach pitches and execute follow-up bumps."""
    console.print(f"[bold cyan]🔍 Scanning CRM for pitches unreplied after {days} days...[/bold cyan]")
    scheduler = AutonomousOutreachScheduler()
    followups = asyncio.run(scheduler.run_followup_sequencing_job(days_threshold=days))

    if not followups:
        console.print("[green]✓ No stale outreach requiring follow-up at this time.[/green]")
        return

    table = Table(title="Triggered Follow-Up Sequences", show_header=True, header_style="bold green")
    table.add_column("Company", style="bold cyan")
    table.add_column("Recipient Email", style="blue")
    table.add_column("Status", style="green")

    for f in followups:
        table.add_row(f.get("company", ""), f.get("lead_email", ""), f.get("status", "FOLLOWED_UP"))

    console.print(table)

@app.command()
def daemon(
    inbox_interval: int = typer.Option(15, "--inbox-interval", help="Interval in minutes for IMAP inbox checks"),
    discovery_interval: int = typer.Option(24, "--discovery-interval", help="Interval in hours for multi-source discovery runs"),
    followup_interval: int = typer.Option(12, "--followup-interval", help="Interval in hours for follow-up sequence checks")
):
    """Launch autonomous background scheduler daemon for periodic discovery, reply monitoring, and HITL Telegram handling."""
    console.print(Panel("🚀 Starting Autonomous Outreach Engine Background Daemon", style="bold blue"))
    console.print(f"• Inbound IMAP Polling: Every [cyan]{inbox_interval}[/cyan] minutes")
    console.print(f"• Prospect Discovery: Every [cyan]{discovery_interval}[/cyan] hours")
    console.print(f"• Follow-Up Sequencing: Every [cyan]{followup_interval}[/cyan] hours")
    console.print(f"• Interactive Telegram Poller: [green]Active (2s loop)[/green]\n")

    scheduler = AutonomousOutreachScheduler()
    try:
        asyncio.run(scheduler.start_daemon(
            inbox_interval_minutes=inbox_interval,
            discovery_interval_hours=discovery_interval,
            followup_interval_hours=followup_interval
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutdown signal received. Stopping daemon...[/yellow]")
        scheduler.stop()
        console.print("[green]✓ Scheduler daemon stopped cleanly.[/green]")

if __name__ == "__main__":
    app()






