# Traditional Security Bug Bounties — HackerOne / Bugcrowd

## Top Programs (USD Rewards)

### HackerOne Platform

| Company | Max Reward | Avg Payout | Notes |
|---------|-----------|-----------|-------|
| Google | $31,337+ | $3,000–$10,000 | VRP, Android, Chrome |
| Microsoft | $250,000 | $5,000–$15,000 | Azure, M365, Xbox |
| Apple | $1,000,000 | — | Invite-only |
| Meta | $500,000 | $1,000–$10,000 | FB, Instagram, WhatsApp |
| Shopify | $500,000 | $500–$5,000 | eCommerce infra |
| Anthropic | $15,000 | — | เพิ่งเปิด public พ.ค. 2026 |

### HackerOne Stats (2025 Annual Report)
- จ่ายรวม $81M USD ในปี 2025 (+13% YoY)
- นักวิจัย 6 คนได้รับเงินรวม >$1M ต่อคน

---

## Bugcrowd Platform

| Company | Max Reward | Focus |
|---------|-----------|-------|
| Tesla | $15,000 | Vehicle software |
| Netgear | $15,000 | Router firmware |
| Various | $300–$3,000 avg | Web apps |

---

## เทคนิค Recon สำหรับ Traditional Bounties

```bash
# subdomain enum
subfinder -d target.com | httpx | nuclei -t exposures/

# JS secret hunting
gau target.com | grep "\.js" | xargs -I {} jsluice urls {}

# Parameter discovery
katana -u https://target.com -jc | uro | qsreplace FUZZ
```

## ช่องโหว่ที่มักจ่ายเงินดี
- SSRF ที่เข้าถึง internal metadata
- Privilege escalation / IDOR ข้ามผู้ใช้
- Auth bypass / JWT flaws
- RCE via template injection
- OAuth misconfigurations
