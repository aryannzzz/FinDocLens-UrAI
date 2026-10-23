"""Real-Chrome smoke check of the packaged offline viewer (no browser download).

Requires installed Chrome and optional requirements-browser.txt. Reads an
extracted ZIP root, uses a disposable profile, never certifies source content.
"""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request


def check(root, out):
    import websocket
    root, out = Path(root).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        raise RuntimeError('Chrome/Chromium not installed; do not download automatically')
    errors=[]
    with tempfile.TemporaryDirectory(prefix='delivery-browser-') as tmp:
        profile=Path(tmp)/'profile'
        with (Path(tmp)/'chrome.log').open('w') as log:
            p=subprocess.Popen([chrome,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
                                '--no-first-run','--no-default-browser-check','--remote-debugging-port=0',
                                '--remote-allow-origins=*','--user-data-dir='+str(profile),
                                (root/'viewer/index.html').as_uri()],stdout=log,stderr=log)
            try:
                active=profile/'DevToolsActivePort'
                deadline=time.monotonic()+15
                while not active.exists() and time.monotonic()<deadline:
                    time.sleep(.1)
                port=active.read_text().splitlines()[0]
                targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
                target=next(t for t in targets if t['type']=='page')
                ws=websocket.create_connection(target['webSocketDebuggerUrl'],timeout=20)
                sequence=0
                def call(method,params=None):
                    nonlocal sequence
                    sequence+=1
                    ws.send(json.dumps(dict(id=sequence,method=method,params=params or {})))
                    while True:
                        message=json.loads(ws.recv())
                        if message.get('method')=='Runtime.exceptionThrown':
                            errors.append(message['params'])
                        if message.get('id')==sequence:
                            if 'error' in message: raise RuntimeError(message['error'])
                            return message['result']
                def js(expression):
                    result=call('Runtime.evaluate',dict(expression=expression,returnByValue=True,userGesture=True))
                    if 'exceptionDetails' in result: raise AssertionError(result['exceptionDetails'])
                    return result['result'].get('value')
                def wait(expression):
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        if js(expression): return
                        time.sleep(.1)
                    raise AssertionError('Timed out: '+expression)
                call('Runtime.enable')
                call('Emulation.setDeviceMetricsOverride',dict(width=1440,height=1050,deviceScaleFactor=1,mobile=False))
                wait('document.readyState==="complete" && !!window.DATA && DATA.docs.length===5')
                pages=[]
                for i in range(5):
                    js(f'document.getElementById("doc").value={i};document.getElementById("doc").dispatchEvent(new Event("change"))')
                    wait('document.getElementById("img").complete && document.getElementById("img").naturalWidth>0')
                    pages.append(js('({id:state.doc.id,width:document.getElementById("img").naturalWidth,height:document.getElementById("img").naturalHeight,backends:Object.keys(state.doc.backends).length})'))
                    for backend in js('Object.keys(state.doc.backends)'):
                        js(f'document.getElementById("backend").value={json.dumps(backend)};document.getElementById("backend").dispatchEvent(new Event("change"))')
                        assert js('document.getElementById("status").textContent.length>0')
                js('document.getElementById("doc").value=0;document.getElementById("doc").dispatchEvent(new Event("change"));document.getElementById("backend").value="native_grid";document.getElementById("backend").dispatchEvent(new Event("change"))')
                js('document.querySelector(\'#tabs [data-k="md"]\').click()')
                assert js('document.getElementById("pane").textContent.includes("△0") && document.getElementById("pane").textContent.includes("－")')
                js('document.querySelector(\'#tabs [data-k="table"]\').click();document.querySelector("#svg .box[data-key]").dispatchEvent(new MouseEvent("click",{bubbles:true}))')
                assert js('!!document.querySelector("#svg .box.sel")')
                js('document.getElementById("zoom").value=170;document.getElementById("zoom").dispatchEvent(new Event("input"))')
                assert js('document.getElementById("stage").style.width')=='170%'
                for tab in ['json','warn','metrics']:
                    js(f'document.querySelector(\'#tabs [data-k="{tab}"]\').click()')
                    assert js('document.getElementById("pane").textContent.length>0')
                assert js('document.getElementById("pane").textContent.includes("unverified draft")')
                wait('document.getElementById("img").complete && document.getElementById("img").naturalWidth>0')
                shot=call('Page.captureScreenshot',dict(format='png'))
                out.with_suffix('.png').write_bytes(base64.b64decode(shot['data']))
                assert not errors,errors
                report=dict(status='pass',source_review_performed=False,pages=pages,backend_views=sum(p['backends'] for p in pages),
                            checks=dict(all_images=True,all_backend_switches=True,markdown_glyphs=True,clickable_evidence=True,zoom=True,json=True,warnings=True,historical_metrics_labeled=True),
                            javascript_errors=errors,browser=call('Browser.getVersion'))
                out.write_text(json.dumps(report,indent=2)+'\n')
                ws.close()
                print(json.dumps(report,indent=2))
            finally:
                p.terminate()
                p.wait(timeout=10)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    check(args.root,args.out)
