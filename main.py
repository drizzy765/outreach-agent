import asyncio
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from database.connection import init_db
from workflow.graph import run_autonomous_outreach_pipeline
from tools.email_verifier import EmailVerifier, generate_email_permutations
from agents.discovery import ProspectDiscoveryAgent
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

    console.print(table)

if __name__ == "__main__":
    app()
