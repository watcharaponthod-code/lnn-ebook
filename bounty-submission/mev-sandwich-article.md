---
title: "MEV Sandwich Attacks on DEX AMMs — Retail Value Extraction and On-Chain Detection"
date: 2026-05-20
description: "Maximal extractable value (MEV) sandwich attacks exploit the predictable price-impact of automated market makers to extract value from retail DEX traders within a single block. This article examines the mechanics, quantifies extraction using EigenPhi and academic on-chain datasets, and reviews the jaredfromsubway.eth case on Ethereum and the Jito mempool shutdown on Solana."
entities:
  - Uniswap
  - Flashbots
  - Ethereum
  - Solana
  - jaredfromsubway.eth
  - Jito Labs
---

## Summary

1. **Documented scale:** A 2024 academic re-measurement identified **3,016,971 sandwich attacks** on Ethereum from July 2015 through August 2023, with conjoined variants yielding approximately 5× higher median profit than single-victim attacks (Qin et al., arxiv 2405.17944).
2. **Single-bot dominance:** The bot `jaredfromsubway.eth` executed **238,000 sandwich attacks** in roughly ten weeks (February–May 2023), generating $40.65 million in gross revenue from victims while paying $34.35 million in gas — a net profit of **$6.3 million** — and affecting over 106,000 victim addresses (EigenPhi, May 2023).
3. **Persistence:** By August 2024, after launching a second-generation bot, the jaredfromsubway operator had accumulated a cumulative lifetime profit of at least **$22 million** since March 2023 (The Block, August 2024). A 2025 EigenPhi dataset attributed roughly **70% of all Ethereum sandwich attacks** to the same entity.
4. **Protocol response:** On March 8, 2024, Jito Labs suspended the mempool feature of its Solana validator client, explicitly stating that sandwich attacks are "a drag on the Solana ecosystem" — an acknowledgement by MEV infrastructure operators that the activity causes identifiable retail harm (CoinDesk, March 2024).
5. **Low average profit, high volume:** Across 95,000+ attacks measured from late 2024 into 2025, the average sandwich profit was just above **$3 per attack**, indicating the strategy is viable at industrial bot scale but not for casual or manual operators (EigenPhi via Cointelegraph, 2025).

## Mechanics

A sandwich attack exploits the deterministic price-impact of constant-product AMMs. In a standard Uniswap v2-style pool governed by `x × y = k`, any pending swap visible in the public mempool will move the price by a predictable amount. An attacker who observes this transaction can:

1. **Front-run:** Submit a buy order in the same pool ahead of the victim's transaction, driving the price upward.
2. **Victim execution:** The victim's swap fills at the artificially elevated price, moving it further in the attacker's favour.
3. **Back-run:** The attacker immediately sells, pocketing the difference between the two execution prices minus gas costs.

The attack is distinct from other manipulation types covered in this wiki. **Wash trading** is self-dealing with no external victim; a sandwich attack extracts value directly from a specific third-party swap. **Oracle manipulation** targets lending protocol price feeds rather than swap execution. **Stop-loss hunting** operates through mark-price movements on centralised perp markets; sandwich attacks require public mempool visibility unique to decentralised blockchains.

For a constant-product pool, the minimum victim trade size at which a sandwich becomes profitable after gas costs can be approximated as:

```
min_victim_USD ≈ (gas_price_gwei × gas_units × eth_price) / slippage_tolerance
```

At 20 gwei gas, 300,000 gas units, and $3,000 ETH, a 1% slippage tolerance implies a break-even victim size of roughly $180. On low-TVL long-tail token pools — where retail traders routinely accept 3–10% slippage — the bar is even lower.

## Detection Approach

On-chain detection of sandwich attacks relies on block-level transaction ordering rather than the OHLCV data used to detect wash trading or oracle manipulation. Three observable signals are used in the literature:

**Transaction-order pattern.** A sandwich produces three transactions in the same block referencing the same liquidity pool: a buy by address A, a swap by a different address, and a sell by address A. Qin et al. (2021) operationalise this as a "displacement" pattern and report detecting 57,037 ETH in sandwich-attributed extraction over their 32-month study window using this criterion alone.

**Execution price deviation.** A sandwiched swap fills at a worse price than the pool's spot price at block start. Comparing the victim's actual execution price against the pre-block pool ratio provides a per-transaction measure of impact. The 2024 re-measurement paper (arxiv 2405.17944) uses this to validate sandwich labels against the ZeroMEV reference dataset, reporting a 2.4% false-negative rate.

**Gas bid asymmetry.** A bot running front-run and back-run legs has strong incentive to outbid the victim on gas precisely — not excessively — to guarantee ordering without sacrificing profit. jaredfromsubway.eth's gas expenditure of $34.35 million against $40.65 million in victim revenue during its first ten weeks implies a gas-to-revenue ratio of roughly 84.5%, which is unusually high and consistent with extremely competitive gas bidding to maintain block position at scale.

Supporting analysis code used to query EigenPhi's labelled dataset and replicate the detection pattern is provided in `analysis.py` in this directory.

## Case Study 1: jaredfromsubway.eth on Ethereum (February–August 2024)

The most extensively documented sandwich operation on any public blockchain is the bot deployed by the address `0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13` (ENS: jaredfromsubway.eth).

**Version 1 (February 21 – ~May 2023).** The original bot contract (`0x6b75d8af000000e20b7a7ddf000ba900b4009a80`, first transaction block 16,673,559) was deployed during the 2023 Ethereum meme coin cycle (PEPE, WOJAK, TURBO). It submitted MEV bundles via Flashbots MEV-Boost relays, guaranteeing atomic sandwich execution within a single block. During the week of April 17, 2023, it appeared in over 60% of all Ethereum blocks — the highest recorded block-inclusion rate for a single MEV bot. By May 8, 2023:

| Metric | Value |
|---|---|
| Gross revenue from victims | $40.65 million |
| Gas fees paid | $34.35 million |
| Net profit | $6.3 million |
| Sandwich attacks executed | 238,000 |
| Victim addresses affected | 106,000+ |

*Source: EigenPhi, "Performance Appraisal of jaredfromsubway.eth," May 2023.*

The high gas-to-revenue ratio reflects the competitive dynamics of MEV-Boost: in a block-auction environment, bots bid up gas costs to maintain ordering priority, compressing net margins even as gross extraction remains large from the victim's perspective.

**Version 2 (August 2024).** A second bot (`0x1f2f10d1c40777ae1da742455c65828ff36df387`) was launched August 14, 2024, introducing multi-layer sandwich attacks — stacking five to seven victim transactions within a single bundle — which increases per-bundle profit while reducing the per-victim detection surface. Between August 1–14, 2024, the original bot alone generated 851 ETH (approximately $2.2 million) in builder rewards across 51,187 transactions, indicating continued large-scale operation before the new bot even launched.

By August 2024, the operator's cumulative lifetime profit was estimated at no less than **$22 million** — a figure that understates total victim losses, since victim revenue of $40.65 million in the first ten weeks alone substantially exceeded net profit.

**Forensic markers:** The Flashbots May–June 2023 Transparency Report confirmed jaredfromsubway.eth "amassed $40.6M in revenue in less than 3 months" and noted that MEV-Boost validators were proposing approximately 90% of Ethereum blocks by that point, meaning nearly all large-pool trades were exposed to bundle-based sandwiching. The report also noted that four relays held 80% of relay market share, concentrating the MEV submission infrastructure through which bots like this one operated.

## Case Study 2: Jito Labs and the Solana Mempool Shutdown (March 2024)

Solana's base architecture processes transactions without an explicit mempool — validators execute batches with no guaranteed ordering within a slot — which theoretically prevents the front-run pattern. Jito Labs' block engine, adopted by a substantial fraction of Solana validators by early 2024, added optional MEV bundle submission with guaranteed in-slot ordering. This replicated the conditions for sandwich attacks on Solana DEXes including Raydium, Orca, and Jupiter-routed swaps.

On **March 8, 2024**, Jito Labs announced suspension of the mempool feature of its Jito-Relayer client software. Lucas Bruder, a Jito Labs contributor, stated directly:

> "Ultimately the Jito Labs team views negative MEV, including sandwich attacks, as a drag on the Solana ecosystem, and in the absence of an engineering solution we have made the difficult decision to suspend the mempool."

The announcement followed a six-week period in which Jito Labs attempted and failed to engineer bundle-rejection logic that would block sandwich attacks while preserving other MEV activity. The suspension was significant for two reasons beyond its immediate effect on sandwich volume. First, it represented an explicit admission by MEV infrastructure operators — who profit from MEV fees — that sandwich attacks cause net harm to the ecosystem. Second, the shutdown drove sandwich activity toward private, opaque mempools rather than eliminating it: operators who had been submitting through Jito's public mempool migrated to private relay services, reducing transparency without reducing the attacks themselves.

A subsequent analysis covering January 2024 through May 2025 — presented at the Solana Accelerate conference by sandwich.me across approximately 8.5 billion trades and ~$1 trillion in DEX volume — estimated total Solana sandwich losses at **$370–$500 million** over that period. The Helius Solana MEV Report provides a detailed breakdown of post-shutdown MEV dynamics on Solana.

## Implications for Retail Traders

Sandwich attacks concentrate on predictable conditions: large slippage tolerance, low pool liquidity, and periods of high retail urgency such as token launches and meme coin cycles. Both case studies above peaked during FOMO-driven retail activity — precisely when traders are least likely to apply protective measures.

**Structural protections** that eliminate the mempool-visibility precondition are the most reliable defence. CoW Protocol's batch auction mechanism matches coinciding orders without sequential AMM execution, removing the front-run opportunity entirely. MEV Blocker, Flashbots Protect RPC, and 1inch Fusion similarly route transactions through private channels before block inclusion. Jupiter on Solana provides MEV protection by default on aggregated routes.

Where these are unavailable — for example, when trading directly on a DEX interface — keeping slippage tolerance at the minimum the pool will accept raises the gas cost required to profit from a sandwich, particularly on high-TVL pairs. A slippage tolerance of 0.5% or below on a liquid pair typically makes the attack unprofitable after gas.

High required slippage on a given token (above 3%) is itself a signal: it indicates pool liquidity is thin enough that a sandwich is cheap to execute, and the liquidity risk and MEV risk are correlated.

## References

- Qin, K., Zhou, L., & Gervais, A. (2021). Quantifying Blockchain Extractable Value: How dark is the forest? *2022 IEEE Symposium on Security and Privacy*. https://arxiv.org/abs/2101.05511
- Qin, K., et al. (2024). Remeasuring Arbitrage and Sandwich Attacks of MEV in Ethereum. https://arxiv.org/html/2405.17944v2
- Daian, P., Goldfeder, S., Kell, T., Li, Y., Zhao, X., Bentov, I., & Juels, A. (2020). Flash Boys 2.0: Frontrunning in Decentralized Exchanges, Miner Extractable Value, and Consensus Instability. *2020 IEEE Symposium on Security and Privacy*. https://doi.org/10.1109/SP40000.2020.00040
- EigenPhi. (2023, May). *Performance Appraisal of jaredfromsubway.eth*. https://coinmarketcap.com/academy/article/eigenphi-performance-appraisal-of-jaredfromsubway.eth
- EigenPhi. (2024, August). *Metamorphosis of jaredfromsubway.eth: Cunninger Jared 2.0 with More Layers*. https://medium.com/@eigenphi/metamorphosis-of-jaredfromsubway-eth-cunninger-jared-2-0-with-more-layers-81a3f900c71a
- Flashbots. (2023). *Flashbots Transparency Report May–June 2023*. https://collective.flashbots.net/t/flashbots-transparency-report-may-june-2023/1927
- Goswami, D. (2024, March 8). Solana Client Developer Jito Announces End of 'Mempool' Function. *CoinDesk*. https://www.coindesk.com/business/2024/03/08/solana-client-developer-jito-announces-end-of-mempool-function
- Blockworks. (2024, March 8). *Jito Labs suspends mempool functionality*. https://blockworks.co/news/jito-labs-suspends-mempool-functionality
- Helius. *Solana MEV Report*. https://www.helius.dev/blog/solana-mev-report
- Cointelegraph / EigenPhi. (2025). *Exclusive data from EigenPhi reveals that sandwich attacks on Ethereum have waned*. https://cointelegraph.com/research/exclusive-data-from-eigenphi-reveals-that-sandwich-attacks-on-ethereum-have-waned
