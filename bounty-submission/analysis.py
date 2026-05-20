"""
Sandwich attack detection on Ethereum using EigenPhi's public labelled dataset.

Replicates the transaction-order pattern approach described in:
  Qin et al. (2021) "Quantifying Blockchain Extractable Value"
  arxiv.org/abs/2101.05511

Data source: EigenPhi sandwich attack CSV export
  https://eigenphi.io/mev/ethereum/sandwich
"""

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class SandwichEvent:
    block: int
    tx_hash_frontrun: str
    tx_hash_victim: str
    tx_hash_backrun: str
    pool: str
    attacker: str
    revenue_usd: float
    cost_usd: float
    profit_usd: float


def load_eigenphi_csv(path: str) -> list[SandwichEvent]:
    """Parse EigenPhi sandwich attack CSV export."""
    events = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                events.append(SandwichEvent(
                    block=int(row["blockNumber"]),
                    tx_hash_frontrun=row["frontrunTxHash"],
                    tx_hash_victim=row["victimTxHash"],
                    tx_hash_backrun=row["backrunTxHash"],
                    pool=row["poolAddress"].lower(),
                    attacker=row["attackerAddress"].lower(),
                    revenue_usd=float(row.get("revenueUSD") or 0),
                    cost_usd=float(row.get("costUSD") or 0),
                    profit_usd=float(row.get("profitUSD") or 0),
                ))
            except (KeyError, ValueError):
                continue
    return events


def attacker_summary(events: list[SandwichEvent]) -> list[dict]:
    """Aggregate profit, revenue, gas cost, and attack count per attacker."""
    agg: dict[str, dict] = defaultdict(lambda: {
        "attacks": 0, "revenue": 0.0, "cost": 0.0, "profit": 0.0
    })
    for e in events:
        a = agg[e.attacker]
        a["attacks"] += 1
        a["revenue"] += e.revenue_usd
        a["cost"] += e.cost_usd
        a["profit"] += e.profit_usd

    rows = [{"attacker": addr, **stats} for addr, stats in agg.items()]
    rows.sort(key=lambda r: r["profit"], reverse=True)
    return rows


def pool_concentration(events: list[SandwichEvent], top_n: int = 10) -> list[dict]:
    """
    Pool Concentration: fraction of a pool's attacks attributable to
    the single most active attacker in that pool.

    A high value (>0.5) indicates one bot dominates that pool's MEV activity.
    """
    pool_attacker: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pool_total: dict[str, int] = defaultdict(int)

    for e in events:
        pool_attacker[e.pool][e.attacker] += 1
        pool_total[e.pool] += 1

    rows = []
    for pool, total in pool_total.items():
        if total < 10:  # skip low-sample pools
            continue
        top_attacker, top_count = max(
            pool_attacker[pool].items(), key=lambda x: x[1]
        )
        rows.append({
            "pool": pool,
            "total_attacks": total,
            "top_attacker": top_attacker,
            "top_attacker_attacks": top_count,
            "concentration": round(top_count / total, 4),
        })

    rows.sort(key=lambda r: r["concentration"], reverse=True)
    return rows[:top_n]


def execution_price_deviation(
    victim_price: float,
    pool_price_at_block_start: float,
) -> float:
    """
    Execution price deviation: how much worse the victim's fill price was
    relative to the pool spot price before the block's MEV transactions.

    Positive value = victim paid more than pre-block spot (consistent with
    front-running).

    References Qin et al. (2021) displacement detection criterion.
    """
    if pool_price_at_block_start == 0:
        raise ValueError("pool_price_at_block_start must be non-zero")
    return (victim_price - pool_price_at_block_start) / pool_price_at_block_start


def gas_revenue_ratio(events: list[SandwichEvent]) -> dict:
    """
    Gas-to-revenue ratio for the full dataset.

    jaredfromsubway.eth v1 (Feb–May 2023) ratio: 34.35M / 40.65M ≈ 0.845.
    A ratio approaching 1.0 indicates hyper-competitive gas bidding to
    maintain block position; the bot is paying nearly all victim revenue
    back to validators.
    """
    total_revenue = sum(e.revenue_usd for e in events)
    total_cost = sum(e.cost_usd for e in events)
    total_profit = sum(e.profit_usd for e in events)
    if total_revenue == 0:
        return {}
    return {
        "total_revenue_usd": round(total_revenue, 2),
        "total_gas_cost_usd": round(total_cost, 2),
        "total_net_profit_usd": round(total_profit, 2),
        "gas_revenue_ratio": round(total_cost / total_revenue, 4),
        "attack_count": len(events),
        "avg_profit_per_attack_usd": round(total_profit / len(events), 4) if events else 0,
    }


def jaredfromsubway_filter(events: list[SandwichEvent]) -> list[SandwichEvent]:
    """
    Filter to known jaredfromsubway.eth bot contracts.
    Addresses from EigenPhi and Etherscan labels.
    """
    jared_addresses = {
        # v1 bot contract
        "0x6b75d8af000000e20b7a7ddf000ba900b4009a80",
        # v2 bot contract (launched August 14, 2024)
        "0x1f2f10d1c40777ae1da742455c65828ff36df387",
        # EOA / owner
        "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13",
    }
    return [e for e in events if e.attacker.lower() in jared_addresses]


def main(csv_path: str) -> None:
    path = Path(csv_path)
    if not path.exists():
        print(f"Data file not found: {csv_path}")
        print("Download from EigenPhi: https://eigenphi.io/mev/ethereum/sandwich")
        return

    events = load_eigenphi_csv(csv_path)
    print(f"Loaded {len(events):,} sandwich events\n")

    print("=== Dataset summary ===")
    summary = gas_revenue_ratio(events)
    print(json.dumps(summary, indent=2))

    print("\n=== Top 5 attackers by net profit ===")
    for row in attacker_summary(events)[:5]:
        print(
            f"  {row['attacker'][:12]}…  "
            f"attacks={row['attacks']:,}  "
            f"profit=${row['profit']:,.0f}  "
            f"gas/revenue={row['cost']/row['revenue']:.3f}" if row['revenue'] else ""
        )

    print("\n=== jaredfromsubway.eth subset ===")
    jared = jaredfromsubway_filter(events)
    if jared:
        print(json.dumps(gas_revenue_ratio(jared), indent=2))
    else:
        print("  No jaredfromsubway events in this dataset slice.")

    print("\n=== Top 10 pools by attacker concentration ===")
    for row in pool_concentration(events):
        print(
            f"  {row['pool'][:12]}…  "
            f"concentration={row['concentration']:.2f}  "
            f"top_attacker={row['top_attacker'][:12]}…  "
            f"attacks={row['total_attacks']:,}"
        )


if __name__ == "__main__":
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "sandwich_data.csv"
    main(csv_file)
