"""Optional real-browser checks; run explicitly, never a core dependency.
Uses only authored local HTML + recorded synthetic data; no browser network requests.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jevkit.engine import catalog,run

def main():
    from playwright.sync_api import sync_playwright
    p=argparse.ArgumentParser();p.add_argument('--browser-binary');a=p.parse_args()
    rows=[run(c['id'],v,persist=False) for c in catalog() for v in ('nominal','adversarial','uncertain')]
    data={'catalog':catalog(),'runs':rows};html=(ROOT/'web/index.html').read_text().replace('<link rel="stylesheet" href="/styles.css">','').replace('<script defer src="/app.js"></script>','')
    checks=0
    with sync_playwright() as pw:
        browser=pw.chromium.launch(**({'executable_path':a.browser_binary} if a.browser_binary else {}))
        page=browser.new_page(viewport={'width':1920,'height':1080});page.route('**/*',lambda route:route.abort())
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html);page.add_style_tag(content=(ROOT/'web/styles.css').read_text())
        page.evaluate('(d) => window.__WORKBENCH_SNAPSHOT__=d',data);page.add_script_tag(content=(ROOT/'web/app.js').read_text())
        page.wait_for_selector('body[data-ready="true"]')
        assert page.locator('#fixture-count').inner_text()=='60';checks+=1
        for row in rows:
            page.evaluate('(s)=>location.hash=s',f'case={row["case_id"]}&mode=fixture&variant={row["variant"]}')
            page.wait_for_function('(id)=>document.body.dataset.runId===id',arg=row['run_id'])
            assert 'SIMULATED' in page.locator('#provenance').inner_text();checks+=1
            assert page.locator('#policy-status').inner_text()==row['policy']['status'].replace('_',' ');checks+=1
        page.select_option('#mode-select','live');page.wait_for_selector('#empty:visible')
        assert 'NO MATCHING RECEIPT' in page.locator('#provenance').inner_text();checks+=1
        page.select_option('#mode-select','fixture');page.wait_for_selector('#evidence:visible')
        page.fill('#case-search','security');assert page.locator('.case-link').count()==1;checks+=1
        page.fill('#case-search','');assert page.locator('.case-link').count()==20;checks+=1
        # Actual narrow phone viewport, not merely a 1080px portrait canvas.
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1');checks+=1
        # Source data is assigned as text, not executed as HTML.
        page.evaluate('''()=>{window.__WORKBENCH_SNAPSHOT__.runs.forEach(r=>r.state={text:'<img src=x onerror="globalThis.PWNED=true">'}); document.getElementById('refresh').click();}''')
        page.wait_for_timeout(100);assert page.evaluate('globalThis.PWNED !== true');checks+=1
        assert not errors,errors;checks+=1
        browser.close()
    print(json.dumps({'browser_checks_passed':checks,'mode':'offline local snapshot','browser_http_navigation_tested':False},indent=2))
if __name__=='__main__':main()
