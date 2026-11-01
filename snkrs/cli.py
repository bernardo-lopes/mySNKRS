"""
Interactive CLI for Sneaker Market Price Valuation.
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.prompt import Prompt

from .models import ConditionGrade, BoxCondition
from .size_converter import SizeConverter
from .platforms.aggregator import MarketplaceAggregator
from .platforms.stockx import CATALOG_BENCHMARKS
from .valuation import SneakerValuationEngine
from .storage import SneakerStorage

console = Console()


@click.group()
def cli():
    """👟 SNKRS - Sneaker Market Price Valuation & Reselling Intelligence"""
    pass


@cli.command()
@click.option("--sku", "-s", default="", help="Sneaker Style Code / SKU (e.g. DD1391-100, DZ5485-612)")
@click.option("--model", "-m", default="", help="Sneaker model name (e.g. Nike Dunk Low Panda)")
@click.option("--size", "-z", default="", help="Size (e.g. US 10, EU 44, 10.5, 42.5)")
@click.option(
    "--condition", "-c",
    type=click.Choice([c.value for c in ConditionGrade]),
    default=ConditionGrade.DEADSTOCK.value,
    help="Sneaker condition (deadstock, vnds, used_good, etc.)"
)
@click.option(
    "--box", "-b",
    type=click.Choice([b.value for b in BoxCondition]),
    default=BoxCondition.ORIGINAL_GOOD.value,
    help="Box condition (original_good, original_damaged, no_box, etc.)"
)
@click.option("--currency", default="EUR", help="Currency (EUR, USD, GBP)")
def estimate(sku: str, model: str, size: str, condition: str, box: str, currency: str):
    """Get market price valuation and reselling check across StockX, GOAT, eBay, and Vinted."""
    asyncio.run(_run_estimate(sku, model, size, condition, box, currency))


async def _run_estimate(sku: str, model: str, size: str, condition_str: str, box_str: str, currency: str):
    console.print("\n[bold cyan]👟 Sneaker Market Price Estimation Tool[/bold cyan]")
    console.print("[dim]Analyzing StockX (Reference), GOAT (Sneakers), eBay (Sold/Active), and Vinted (0% fees)...[/dim]\n")

    # Interactive prompts if missing inputs
    if not sku and not model:
        sku = Prompt.ask("[bold green]Enter Sneaker SKU or Model Reference[/bold green] (e.g. DD1391-100 or DZ5485-612)").strip()
    if not size:
        size = Prompt.ask("[bold green]Enter Sneaker Size[/bold green] (e.g. US 10, EU 44, UK 9.5)").strip()

    cond_enum = ConditionGrade(condition_str)
    box_enum = BoxCondition(box_str)

    norm_size = SizeConverter.normalize(size)
    size_label = SizeConverter.format_all_sizes(size)

    with console.status("[bold yellow]Querying marketplaces and analyzing market data...[/bold yellow]", spinner="dots"):
        aggregator = MarketplaceAggregator()
        platform_data = await aggregator.aggregate(
            sku=sku,
            model_name=model,
            size_us=norm_size["us_m"],
            size_eu=norm_size["eu"],
            condition=cond_enum,
            box_condition=box_enum,
            currency=currency
        )
        report = SneakerValuationEngine.evaluate(
            sku=sku,
            size_input=size,
            condition=cond_enum,
            box_condition=box_enum,
            platforms_data=platform_data,
            model_name=model,
            currency=currency
        )

    # Save to history
    storage = SneakerStorage()
    storage.save_evaluation(report)

    # 1. Header Card
    header_text = Text()
    header_text.append(f"{report.brand} ", style="bold white")
    header_text.append(f"{report.model_name}\n", style="bold yellow")
    header_text.append(f"SKU: {report.sku} | Size: {size_label}\n", style="cyan")
    header_text.append(f"Condition: {report.condition.value.upper()} | Box: {report.box_condition.value.upper()}\n", style="magenta")
    if report.retail_price:
        header_text.append(f"Retail Price: €{report.retail_price} | StockX DS Benchmark: €{report.stockx_reference_price}", style="dim")

    console.print(Panel(header_text, title="👟 SNEAKER DETAILS", border_style="cyan"))

    # 2. Price Strategy Summary Panels
    p_quick = Panel(
        f"[bold red]€{report.quick_sale_price}[/bold red]\n[dim]Sell in 24-48h\nUndercut ask or hit bids[/dim]",
        title="⚡ Quick Flip",
        border_style="red"
    )
    p_fair = Panel(
        f"[bold green]€{report.fair_market_price}[/bold green]\n[dim]Target Sell Price\nOptimal within 1-2 wks[/dim]",
        title="🎯 Fair Market",
        border_style="green"
    )
    p_patient = Panel(
        f"[bold blue]€{report.patient_sale_price}[/bold blue]\n[dim]Collector Value\nFor patient sellers[/dim]",
        title="💎 Maximum Value",
        border_style="blue"
    )
    console.print(Columns([p_quick, p_fair, p_patient], equal=True))

    # 3. Marketplace Comparison Table
    table = Table(title="📊 MARKETPLACE PRICE & NET TAKE-HOME BREAKDOWN", header_style="bold magenta")
    table.add_column("Marketplace", style="bold white", width=14)
    table.add_column("Condition Focus", style="dim", width=16)
    table.add_column("Lowest Ask", justify="right", width=12)
    table.add_column("Fee Structure", justify="right", width=14)
    table.add_column("Net Take-Home Cash", justify="right", style="bold green", width=18)
    table.add_column("Platform Advantage", style="cyan")

    for pid, pdata in report.platforms.items():
        if not pdata:
            continue
        ask_str = f"€{pdata.lowest_ask}" if pdata.lowest_ask else "N/A"
        fee_str = f"{pdata.seller_fee_percentage}% + €{pdata.seller_fixed_fee}" if pdata.seller_fee_percentage > 0 else "0% (Free!)"
        payout_str = f"€{pdata.estimated_net_payout}" if pdata.estimated_net_payout else "N/A"
        
        focus = {
            "stockx": "Deadstock Only",
            "goat": "New & Used Pairs",
            "ebay": "Active & Sold",
            "vinted": "Peer-to-Peer 0%"
        }.get(pid, "General")

        table.add_row(
            pdata.platform_name,
            focus,
            ask_str,
            fee_str,
            payout_str,
            pdata.notes or ""
        )

    console.print(table)

    # 4. Best Selling Recommendation
    best_text = Text()
    best_text.append(f"🏆 Best Platform to Sell: ", style="bold")
    best_text.append(f"{report.best_platform_to_sell}\n", style="bold underline green")
    best_text.append(f"{report.best_platform_reason}\n\n", style="white")

    if report.insights:
        best_text.append("💡 Reselling Insights & Action Plan:\n", style="bold yellow")
        for tip in report.insights:
            clean_tip = tip.replace("**", "")
            best_text.append(f" • {clean_tip}\n", style="dim white")

    console.print(Panel(best_text, title="🚀 SELLING STRATEGY", border_style="green"))


@cli.command(name="popular")
def popular():
    """List popular sneaker benchmark references."""
    table = Table(title="🔥 Popular Sneaker Reference Catalog", header_style="bold yellow")
    table.add_column("SKU", style="bold cyan")
    table.add_column("Model Name", style="white")
    table.add_column("Retail", justify="right")
    table.add_column("StockX DS Ref", justify="right", style="bold green")

    for sku, item in CATALOG_BENCHMARKS.items():
        table.add_row(
            sku,
            item["title"],
            f"€{item['retail_price']}",
            f"€{item['base_stockx_ds']}"
        )
    console.print(table)


@cli.command(name="history")
def history():
    """View recent sneaker valuation history."""
    storage = SneakerStorage()
    recent = storage.get_recent_evaluations(10)
    if not recent:
        console.print("[yellow]No valuations recorded yet. Run `snkrs estimate` first![/yellow]")
        return

    table = Table(title="🕒 Recent Sneaker Valuations", header_style="bold cyan")
    table.add_column("Date", style="dim")
    table.add_column("SKU", style="bold white")
    table.add_column("Model", style="white")
    table.add_column("Size", justify="center")
    table.add_column("Condition", style="magenta")
    table.add_column("Fair Market", justify="right", style="bold green")
    table.add_column("Best Platform", style="cyan")

    for r in recent:
        table.add_row(
            str(r["created_at"])[:16],
            r["sku"],
            r["model_name"][:25] if r["model_name"] else "-",
            r["size_input"],
            r["condition"],
            f"€{r['fair_market_price']}",
            r["best_platform"]
        )
    console.print(table)


@cli.command(name="web")
@click.option("--host", default="127.0.0.1", help="Host interface")
@click.option("--port", default=8000, help="Port to listen on")
def web(host: str, port: int):
    """Launch the Web Dashboard for Sneaker Market Price Estimation."""
    import uvicorn
    console.print(f"[bold green]Starting SNKRS Web Dashboard at http://{host}:{port}[/bold green]")
    uvicorn.run("snkrs.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    cli()
