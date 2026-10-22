"""Optional real-Chrome smoke test; uses an isolated profile and dummy decisions only.

Needs Chrome and websocket-client (already present in the review environment).
No browser/model download. Never saves test decisions to the repository.
"""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.common import commit, sha256, utc


def run(url, out, expect_broken=False):
    import websocket
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        raise RuntimeError('Chrome/Chromium is not installed')
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise FileExistsError(out)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='source-review-browser-') as tmp:
        profile, downloads = Path(tmp)/'profile', Path(tmp)/'downloads'
        downloads.mkdir()
        with (Path(tmp)/'chrome.log').open('w') as log:
            process = subprocess.Popen([chrome, '--headless=new', '--no-sandbox', '--disable-gpu',
                                        '--no-proxy-server', '--disable-dev-shm-usage', '--no-first-run',
                                        '--no-default-browser-check', '--remote-debugging-port=0',
                                        '--remote-allow-origins=*', '--user-data-dir='+str(profile), url],
                                       stdout=log, stderr=log)
            try:
                active = profile/'DevToolsActivePort'
                for _ in range(150):
                    if active.exists():
                        break
                    if process.poll() is not None:
                        raise RuntimeError('Chrome exited before DevTools started')
                    time.sleep(.1)
                port = active.read_text().splitlines()[0]
                # Chrome also exposes component extension background pages. Only attach
                # to the actual page, never the first target in /json.
                targets = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
                target = next(t for t in targets if t['type'] == 'page')
                ws = websocket.create_connection(target['webSocketDebuggerUrl'], timeout=20)
                sequence = 0

                def call(method, params=None):
                    nonlocal sequence
                    sequence += 1
                    ws.send(json.dumps(dict(id=sequence, method=method, params=params or {})))
                    while True:
                        message = json.loads(ws.recv())
                        if message.get('id') == sequence:
                            if 'error' in message:
                                raise RuntimeError(message['error'])
                            return message['result']

                def js(expression):
                    response = call('Runtime.evaluate', dict(expression=expression, returnByValue=True, userGesture=True))
                    if 'exceptionDetails' in response:
                        raise AssertionError(response['exceptionDetails'])
                    return response['result'].get('value')

                def wait(expression):
                    deadline = time.monotonic()+15
                    while time.monotonic() < deadline:
                        if js(expression):
                            return
                        time.sleep(.1)
                    raise AssertionError('Timed out: '+expression)

                def screenshot(name):
                    image = call('Page.captureScreenshot', dict(format='png'))
                    path = out.parent/(out.stem+'_'+name+'.png')
                    path.write_bytes(base64.b64decode(image['data']))
                    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

                call('Emulation.setDeviceMetricsOverride', dict(width=1440, height=1080, deviceScaleFactor=1, mobile=False))
                wait('document.readyState === "complete"')
                report = dict(timestamp=utc(), git_commit=commit(), url=url, browser=call('Browser.getVersion'),
                              test_decisions='AUTOMATED_UI_TEST_NOT_HUMAN; isolated profile, temporary download deleted',
                              pages=[], checks={})
                if expect_broken:
                    report['broken_images'] = js('[...document.images].filter(i=>!i.naturalWidth).map(i=>i.getAttribute("src"))')
                    assert report['broken_images']
                    report['screenshot'] = screenshot('broken')
                else:
                    wait('!!window.reviewApp && Object.values(reviewApp.images).every(i=>i.complete && i.naturalWidth>0)')
                    cases = [('original', 'assets_r012', 1, '△0', 'accepted'),
                             ('elecom_p9', 'assets_r031', 0, '△4', 'correction_needed'),
                             ('daiwabo_p10', 'assets_r002', 2, '△43,010', 'unreadable')]
                    for did, row, column, raw, decision in cases:
                        key = f'{did}:{row}:{column}'
                        js(f'document.getElementById("document").value={json.dumps(did)};document.getElementById("document").dispatchEvent(new Event("change"))')
                        wait(f'document.getElementById("source-page").complete && document.getElementById("source-page").naturalWidth>0 && document.getElementById("source-page").src.includes({json.dumps(did+"_page.png")})')
                        q = json.dumps(f'button[aria-label="Inspect source {key}"]')
                        assert js(f'document.querySelector({q}).textContent') == raw
                        js('document.getElementById("page-zoom").value=125;document.getElementById("page-zoom").dispatchEvent(new Event("input"));document.getElementById("detail-zoom").value=200;document.getElementById("detail-zoom").dispatchEvent(new Event("input"))')
                        js(f'document.querySelector({q}).click()')
                        source = js('({src:document.getElementById("source-page").src,width:document.getElementById("source-page").naturalWidth,height:document.getElementById("source-page").naturalHeight,detailWidth:document.getElementById("detail").width,detailHeight:document.getElementById("detail").height,pageZoom:document.getElementById("page-zoom-value").textContent,detailZoom:document.getElementById("detail-zoom-value").textContent,highlight:getComputedStyle(document.getElementById("selection-box")).display})')
                        assert source['detailWidth'] > 0 and source['detailHeight'] > 0
                        assert source['pageZoom'] == '125%' and source['detailZoom'] == '200%'
                        assert source['highlight'] == 'block'
                        if url.startswith('http'):
                            assert js('Array.from(document.getElementById("detail").getContext("2d").getImageData(0,0,document.getElementById("detail").width,document.getElementById("detail").height).data).some((v,i)=>i%4!==3&&v<180)')
                        source['screenshot'] = screenshot(did)
                        source['document_id'], source['raw_inspected'] = did, raw
                        report['pages'].append(source)
                        selector = json.dumps(f'select[aria-label="Decision {key}"]')
                        js(f'document.querySelector({selector}).value={json.dumps(decision)};document.querySelector({selector}).dispatchEvent(new Event("change"))')
                        if decision == 'correction_needed':
                            note = json.dumps(f'input[aria-label="Correction {key}"]')
                            js(f'document.querySelector({note}).value="AUTOMATED_UI_TEST: dummy note, not a correction";document.querySelector({note}).dispatchEvent(new Event("input"))')
                    js('reviewApp.selectDocument("original");[...document.querySelectorAll(".row-title")].find(n=>n.textContent.startsWith("assets_r026 ")).click()')
                    assert js('document.getElementById("detail-title").textContent.includes("建設仮勘定")')
                    assert js('document.getElementById("detail").width > 500')
                    report['japanese_row_screenshot'] = screenshot('japanese_row')
                    js('document.querySelector(\'button[aria-label="Inspect source original:assets_r026:0"]\').click()')
                    assert js('document.getElementById("detail-title").textContent.includes("－")')
                    report['dash_screenshot'] = screenshot('dash')
                    report['checks'].update(japanese_row_zoom=True, dash_zoom=True)
                    js('document.getElementById("reviewer").value="AUTOMATED_UI_TEST_NOT_HUMAN";document.getElementById("reviewer").dispatchEvent(new Event("input"));document.getElementById("scope").value="Automated interface test only, no human verification";document.getElementById("scope").dispatchEvent(new Event("input"))')
                    call('Page.reload')
                    wait('!!window.reviewApp && document.getElementById("progress").textContent.startsWith("3 / 197")')
                    report['checks']['draft_survives_reload'] = True
                    call('Browser.setDownloadBehavior', dict(behavior='allow', downloadPath=str(downloads)))
                    js('document.getElementById("export").click()')
                    download = downloads/'human_review_decisions.json'
                    deadline = time.monotonic()+10
                    while not download.exists() and time.monotonic() < deadline:
                        time.sleep(.1)
                    exported = json.loads(download.read_text())
                    assert exported['reviewer'] == 'AUTOMATED_UI_TEST_NOT_HUMAN'
                    assert exported['human_verification_applied'] is False
                    assert len(exported['decisions']) == 197
                    changed = [d for d in exported['decisions'] if d['decision'] != 'unreviewed']
                    assert {d['decision'] for d in changed} == {'accepted', 'correction_needed', 'unreadable'}
                    assert {d['expected_raw'] for d in changed} == {'△0', '△4', '△43,010'}
                    dash = next(d for d in exported['decisions'] if d['key'] == 'original:assets_r026:0')
                    assert (dash['expected_raw'], dash['expected_value'], dash['expected_status'], dash['decision']) == ('－', None, 'not_reported', 'unreviewed')
                    assert all(d['gold_sha256'] and d['source_sha256'] and d['bbox'] for d in changed)
                    report['checks'].update(json_download=True, all_197_cells_exported=True, all_decision_types=True,
                                            original_glyphs_preserved=True, evidence_identity_exported=True,
                                            human_verification_applied=False)
                    if url.startswith('http'):
                        call('Network.enable')
                        call('Network.setCacheDisabled', dict(cacheDisabled=True))
                        call('Network.setBlockedURLs', dict(urls=['*elecom_p9_page.png']))
                        call('Page.reload')
                        wait('!!window.reviewApp && !document.getElementById("image-error").hidden')
                        js('reviewApp.selectDocument("elecom_p9")')
                        assert js('[...document.querySelectorAll(".decision-fields select")].every(s=>s.disabled)')
                        assert js('document.getElementById("detail").width === 1')
                        report['checks']['missing_image_visible_and_decisions_disabled'] = True
                report['elapsed_ms'] = (time.perf_counter()-started)*1000
                report['status'] = 'pass'
                out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
                ws.close()
                print(json.dumps(dict(status='pass', output=str(out), checks=report.get('checks'), pages=len(report['pages'])), indent=2))
            finally:
                process.terminate()
                process.wait(timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8765/benchmark/review/')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expect-broken', action='store_true')
    args = parser.parse_args()
    run(args.url, args.out, args.expect_broken)
