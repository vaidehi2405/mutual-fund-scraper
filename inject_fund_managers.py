import json
from pathlib import Path
from datetime import datetime, timezone

# Path to the chunks file
CHUNKS_PATH = Path('data/processed/chunks.jsonl')

# Manager data extracted from Groww (plain text)
MANAGER_DATA = {
    'large_cap': """Sankaran Naren (Feb 2026 – Present)\nEducation: B.Tech from IIT Chennai and MBA (Finance) from IIM Kolkata.\nExperience: Worked with Refco Sify Securities India Pvt. Ltd., HDFC Securities Ltd., and Yoha Securities.\n\nVaibhav Dusad (Jan 2021 – Present)\nEducation: B.Tech, M.Tech, and MBA.\nExperience: Previously worked with Morgan Stanley, HSBC Global Banking and Markets, CRISIL, Zinnov Management Consulting, and Citibank Singapore.\n\nSharmila D’Silva (Mar 2026 – Present)\nEducation: CA and BAF.\nExperience: Joined ICICI Prudential AMC Limited in September 2016.""",
    'midcap': """Lalit Kumar (Aug 2022 – Present)\nEducation: PGDM (IIM) and B.Tech in Electrical Engineering (IIT).\nExperience: Prior to joining ICICI Prudential Mutual Fund, he worked with East Bridge Advisors Pvt. Ltd, Nomura Financial Advisory & Securities, Merrill Lynch and Cypress Semiconductors.\n\nSharmila D’Silva (Jul 2022 – Present)\nEducation: CA and BAF.\nExperience: Joined ICICI Prudential AMC Limited in September 2016.""",
    'flexicap': """Rajat Chandak (Jun 2021 – Present)\nEducation: B.Com (H) and MBA.\nExperience: Associated with ICICI Prudential AMC since 2008.\n\nSharmila D’Silva (Jul 2022 – Present)\nEducation: CA and BAF.\nExperience: Joined ICICI Prudential AMC Limited in September 2016.""",
    'elss': """Mittul Kalawadia (Sep 2023 – Present)\nEducation: B.Com from Mithibai College, M.Com from University of Mumbai, and CA from ICAI.\nExperience: Associated with ICICI Prudential since 2012.\n\nPriyanka Khandelwal (Mar 2026 – Present)\nEducation: Chartered Accountant and Company Secretary.\nExperience: Working with ICICI Prudential Mutual Fund since October 2014.\n\nSharmila D’Silva (Jul 2022 – Present)\nEducation: CA and BAF.\nExperience: Joined ICICI Prudential AMC Limited in September 2016."""
}

def append_manager_chunks():
    if not CHUNKS_PATH.exists():
        print('Chunks file not found!')
        return
    with open(CHUNKS_PATH, 'a', encoding='utf-8') as f:
        for scheme, text in MANAGER_DATA.items():
            chunk = {
                'chunk_id': f'manual_{scheme}_fund_manager_01',
                'run_id': f'manual_import_{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}',
                'source_id': f'manual_groww_{scheme}',
                'url': f'https://groww.in/mutual-funds/icici-prudential-{scheme.replace("_","-")}-fund-direct-growth',
                'domain': 'groww.in',
                'fund': scheme.replace('_', ' '),
                'amc': 'ICICI Prudential AMC',
                'scheme': scheme,
                'doc_type': 'Groww scheme specific data and FAQs',
                'section_title': 'Fund Management',
                'published_or_effective_date': '',
                'ingested_at': datetime.now(timezone.utc).isoformat(),
                'text': text
            }
            f.write(json.dumps(chunk, ensure_ascii=True) + '\n')
            print(f'✅ Added manager chunk for {scheme}')

if __name__ == '__main__':
    append_manager_chunks()
