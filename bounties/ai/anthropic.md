# Anthropic Bug Bounty — HackerOne

## Overview
- **Platform:** HackerOne (Public — เพิ่งเปิดสาธารณะ 8 พ.ค. 2026)
- **Status:** 🟢 OPEN
- **Max Reward:** $15,000 USD
- **Program Type:** AI Safety / Security

## Reward Tiers

### Model Safety Bug Bounty (จ่ายเงิน)
เน้น jailbreak ที่ universal และ novel ต่อ Constitutional Classifiers ใน domain ความเสี่ยงสูง:
- Chemical, Biological, Radiological, Nuclear (CBRN)
- Cybersecurity threats

| Severity | Reward |
|----------|--------|
| Critical (universal jailbreak) | $10,000 – $15,000 |
| High | $5,000 – $9,999 |
| Medium | $1,000 – $4,999 |

### Infrastructure / Traditional Security (จ่ายเงิน)
- CSRF, Privilege Escalation, SQL Injection, XSS, Directory Traversal

## What to Look For
- Prompt injection ที่ข้ามข้อจำกัด CBRN
- Jailbreak แบบ universal ที่ทำงานได้ข้ามหลาย session
- Safety classifier bypass สำหรับ cybersecurity content
- ช่องโหว่ infrastructure ของ Anthropic Console / API

## Links
- Program page: https://hackerone.com/anthropic-ai
- Policy blog: https://www.anthropic.com/security

## Notes
- ก่อนหน้านี้เป็น private program, เปิด public 8 พ.ค. 2026
- Competition จะสูงขึ้นเรื่อยๆ ยิ่งเจอเร็วยิ่งดี
