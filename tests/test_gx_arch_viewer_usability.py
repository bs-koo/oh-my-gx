"""읽기·탐색·실패 표시와 모듈 근거의 사용자 계약을 검증한다."""
import importlib.util
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from urllib.parse import unquote
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.claude/skills/gx-visualize/scripts'


class BrowserTemporaryDirectory(tempfile.TemporaryDirectory):
    """Windows Crashpad가 종료 직후 잠깐 유지하는 프로필 파일 잠금을 기다린다."""
    def cleanup(self):
        deadline = time.monotonic() + 5
        while True:
            try:
                return super().cleanup()
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.1)


def load(name):
    spec = importlib.util.spec_from_file_location('usability_' + name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def document():
    return {'schema_version': 1, 'view': 'service', 'locale': 'ko-KR', 'title': '사용자 구조',
            'nodes': [{'id': 'api id/한글', 'kind': 'api', 'label': '사용자 조회', 'symbol': 'UserController.list', 'technical_label': 'GET /users', 'status': 'unknown', 'evidence': []},
                      {'id': 'service', 'kind': 'service', 'label': '감사 기록', 'status': 'unknown', 'external_domain': 'audit test', 'evidence': []}],
            'edges': [{'id': 'edge', 'source': 'api id/한글', 'target': 'service', 'relation': 'depends_on'}],
            'meta': {'navigation': {'domain': 'user', 'domains': ['user', 'audit test']}}}


class ViewerUsabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fallback = load('render_fallback')
        cls.viewer = load('viewer_shell')
        cls.archify = load('render_archify')

    def test_names_symbols_navigation_and_external_links_are_present(self):
        html = self.fallback._render_document(document(), 'static')
        self.assertIn('<h3>사용자 조회</h3>', html)
        self.assertIn('UserController.list', html)
        self.assertIn('GET /users', html)
        self.assertIn('<summary>내부 ID</summary>', html)
        self.assertIn('href="../%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98-%EB%A7%B5.html"', html)
        self.assertIn('href="audit%20test.html#gx-detail-service"', html)
        self.assertIn('타입 의존', html)
        self.assertIn('들어오는 관계', html)
        self.assertIn('나가는 관계', html)
        self.assertNotIn('status-unknown">확인 필요', html)

    def test_unicode_and_pathlike_node_id_round_trip(self):
        node = document()['nodes'][0]
        self.assertEqual(self.viewer.anchor(node['id']), unquote(self.viewer.node_href(node)[1:]))
        self.assertIn('id="gx-detail-api id/한글"', self.viewer.explorer(document()))

    def test_feature_picker_uses_local_entrypoints_and_keeps_full_evidence(self):
        ir = document()
        ir['nodes'][0]['technical_label'] = 'GET /orders'
        ir['nodes'][0]['routes'] = ['GET /orders', 'GET /purchases']
        ir['nodes'].append({'id': 'external-api', 'kind': 'api', 'label': '다른 API', 'external_domain': 'other', 'status': 'unknown', 'evidence': []})
        feature = self.viewer.feature_explorer(ir)
        self.assertIn('data-gx-feature="api id/한글"', feature)
        self.assertNotIn('data-gx-feature="external-api"', feature)
        self.assertIn('GET /orders · GET /purchases', feature.split('<script', 1)[0])
        self.assertIn('클래스 단위 연결', feature)
        self.assertIn('실제 실행 경로나 소요 시간', feature)
        html = self.fallback._render_document(ir, 'static')
        self.assertIn('id="gx-features"', html)
        self.assertIn('id="gx-full-map"', html)
        self.assertIn('data-gx-collapse-on-ready', html)
        self.assertIn('<details class="gx-full-evidence">', html)
        self.assertIn('id="gx-detail-api id/한글"', html)

    def test_feature_payload_is_safe_and_does_not_mutate_source_ir(self):
        ir = document()
        ir['nodes'][0]['label'] = '</script><img src=x onerror=alert(1)>'
        ir['nodes'][0]['id'] = 'api/값%20'
        ir['edges'][0]['source'] = 'api/값%20'
        original = json.dumps(ir, sort_keys=True)
        markup = self.viewer.feature_explorer(ir)
        value = markup.split('<script type="application/json" id="gx-feature-data">', 1)[1].split('</script>', 1)[0]
        payload = json.loads(value)
        self.assertEqual(ir['nodes'][0]['label'], payload['nodes'][0]['label'])
        self.assertEqual(['api/값%20'], payload['features'])
        self.assertNotIn('<img', markup)
        self.assertNotIn('</script><img', markup)
        self.assertEqual(original, json.dumps(ir, sort_keys=True))

    def test_non_service_and_domains_without_entrypoints_keep_original_view(self):
        ir = document()
        ir['view'] = 'trace'
        self.assertEqual('', self.viewer.feature_explorer(ir))
        ir['view'] = 'service'
        ir['nodes'] = [node for node in ir['nodes'] if node['kind'] != 'api']
        self.assertEqual('', self.viewer.feature_explorer(ir))

    def test_unavailable_domains_and_external_nodes_do_not_link_to_absent_files(self):
        ir = document()
        ir['meta']['navigation']['domains'] = ['user', {'name': 'audit test', 'available': False}]
        ir['nodes'][1]['external_available'] = False
        nav = self.viewer.navigation(ir)
        self.assertIn('aria-disabled="true"', nav)
        self.assertNotIn('href="audit%20test.html', nav)
        self.assertEqual('#gx-detail-service', self.viewer.node_href(ir['nodes'][1]))
        detail = self.viewer.explorer(ir)
        self.assertIn('현재 결과 없음', detail)
        self.assertNotIn('href="audit%20test.html', detail)

    def test_detail_id_does_not_duplicate_archify_svg_node_id(self):
        class IDs(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []
            def handle_starttag(self, tag, attrs):
                self.ids.extend(value for key, value in attrs if key == 'id')
        ir = document()
        svg = '<svg>' + ''.join(f'<g id="node-{html.escape(node["id"], quote=True)}"></g>' for node in ir['nodes']) + '</svg>'
        parsed = IDs()
        parsed.feed(svg + self.viewer.explorer(ir))
        self.assertEqual(len(parsed.ids), len(set(parsed.ids)))
        self.assertIn('node-api id/한글', parsed.ids)
        self.assertIn('gx-detail-api id/한글', parsed.ids)

    def test_untrusted_labels_and_domains_remain_text_or_encoded_paths(self):
        ir = document()
        ir['nodes'][0]['label'] = '<img src=x onerror=alert(1)>'
        ir['nodes'][1]['external_domain'] = 'javascript:alert(1)/../'
        html = self.viewer.explorer(ir)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;img', html)
        self.assertNotIn('href="javascript:', html)

    def test_source_link_is_confined_to_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self.viewer.evidence_html([{'kind': 'code', 'file': 'src/User.java', 'line': 4}], tmp)
            self.assertIn('vscode://file/', html)
            self.assertIn('User.java:4', html)
            escaped = self.viewer.evidence_html([{'kind': 'code', 'file': '../secret.txt', 'line': 1}], tmp)
            self.assertNotIn('href=', escaped)

    def test_diagnostics_preserve_actionable_target_and_file(self):
        ir = document()
        ir['meta']['unresolved_edges'] = [{'reason': 'unresolved-target', 'target': 'MissingService', 'file': 'User.java', 'line': 8}]
        ir['missing_inputs'] = ['디자인 문서']
        html = self.viewer.diagnostics(ir)
        for value in ['확인이 필요한 항목', 'MissingService', 'User.java', '디자인 문서', '다시 생성']:
            self.assertIn(value, html)

    def test_nested_diagnostic_evidence_is_visible_and_navigable(self):
        ir = document()
        ir['meta']['unresolved_edges'] = [{'reason': 'unresolved-target', 'target': 'MissingService',
                                         'evidence': [{'kind': 'code', 'file': 'src/User.java', 'line': 8}]}]
        with tempfile.TemporaryDirectory() as tmp:
            html = self.viewer.diagnostics(ir, tmp)
        self.assertIn('src/User.java:8', html)
        self.assertIn('vscode://file/', html)

    def test_browser_hash_keyboard_and_legacy_links_select_detail_article(self):
        chrome = shutil.which('google-chrome') or shutil.which('chromium')
        if not chrome:
            candidate = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
            chrome = str(candidate) if candidate.is_file() else None
        if not chrome:
            self.skipTest('Chrome is required for real SVG/HTML focus verification')
        node = shutil.which('node')
        self.assertIsNotNone(node, 'The Chrome CDP test requires the repository Node runtime')
        ir = document()
        ir['nodes'].append({'id': 'node-가격%20/원래', 'kind': 'service', 'label': '퍼센트 식별자', 'status': 'unknown', 'evidence': []})
        page = self.fallback._render_document(ir, 'mermaid', mermaid_asset_href='fake-mermaid.js')
        # 실제 SVG와 article을 한 DOM에 넣고, Mermaid 비동기 완료 뒤 연결되는 실제 핸들러를 사용한다.
        page = page.replace('<script src="fake-mermaid.js"></script>', '<script>window.mermaid={initialize(){},async run(){document.querySelector(".mermaid").innerHTML=\'<svg viewBox="0 0 640 120"><g class="node" id="flowchart-n0-0"><text>API</text></g></svg>\'}}</script>')
        svg = '<svg><g id="node-api id/한글" data-node-id="api id/한글" tabindex="0"><text>Archify API</text></g></svg>'
        page = page.replace('<body>', '<body>' + svg, 1)
        checks = r'''<script>
window.runGXViewerChecks = async () => {
  const results = [];
  const pause = () => new Promise(resolve => setTimeout(resolve, 10));
  const check = (name, ok) => results.push({name, ok});
  const select = async id => { location.hash=encodeURIComponent(id); await pause(); };
  const article = document.getElementById('gx-detail-api id/한글');
  const ids = [...document.querySelectorAll('[id]')].map(node=>node.id);
  check('unique SVG and article IDs', ids.length===new Set(ids).size);
  const search = document.querySelector('#gx-node-search'); search.value='absent'; search.dispatchEvent(new Event('input'));
  await select('gx-detail-api id/한글');
  check('unicode hash reveals and focuses article', document.activeElement===article && !article.parentElement.hidden && search.value==='');
  await select('node-api id/한글');
  check('legacy hash canonicalized to detail', decodeURIComponent(location.hash.slice(1))==='gx-detail-api id/한글' && document.activeElement===article);
  await select('gx-detail-node-가격%20/원래');
  check('percent is decoded exactly once', document.activeElement.id==='gx-detail-node-가격%20/원래');
  document.querySelector('[data-node-id]').dispatchEvent(new MouseEvent('dblclick',{bubbles:true})); await pause();
  check('Archify dblclick focuses article', document.activeElement===article);
  for(const key of ['Enter',' ']) {
    await select('gx-detail-service');
    document.querySelector('.mermaid .node').dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true})); await pause();
    check('Mermaid keyboard '+key, document.activeElement===article);
  }
  // Archify는 한 화면에 맞추며 넓힘/overflow 보정을 번갈아 적용한다.
  // 긴 GX 문서는 이 변수에 의해 실제 도식 폭이 진동하지 않아야 한다.
  const sizingStyle=document.createElement('style');
  sizingStyle.textContent='.container{width:100%;max-width:var(--archify-reader-width,1440px)}html[data-present="true"] .container,html[data-embed="true"] .container{max-width:none}';
  document.head.prepend(sizingStyle);
  const fixture=document.createElement('div');fixture.className='gx-archify';fixture.style.width='1100px';
  fixture.innerHTML='<div class="container" style="height:1200px"></div>';document.body.append(fixture);
  const stage=fixture.firstElementChild;
  document.documentElement.style.setProperty('--archify-reader-width','1376px');await pause();
  const wide=stage.getBoundingClientRect().width;
  document.documentElement.style.setProperty('--archify-reader-width','960px');await pause();
  check('long document ignores viewport fitting width oscillation',wide>1000&&stage.getBoundingClientRect().width===wide);
  for(const mode of ['data-present','data-embed']) {
    document.documentElement.setAttribute(mode,'true');
    check(mode+' retains original sizing override',getComputedStyle(stage).maxWidth==='none');
    document.documentElement.removeAttribute(mode);
  }
  fixture.style.width='320px';
  check('document sizing stays fluid on mobile',stage.getBoundingClientRect().width===320);
  fixture.remove();sizingStyle.remove();document.documentElement.style.removeProperty('--archify-reader-width');
  const result=document.createElement('pre');result.id='gx-browser-results';result.textContent=JSON.stringify(results);document.body.append(result);
  return results;
};</script>'''
        page = page.replace('</body>', checks + '</body>')
        # Chrome 프로필을 OS 사용자 로컬 폴더에 고정한다. 프로젝트용 TEMP 재지정과 분리한다.
        # 재지정 TEMP에서 멎던 초기 탐색이 동일 HTML/driver의 사용자 로컬 프로필에서 통과했다.
        browser_temp = Path(os.environ['LOCALAPPDATA']) / 'Temp' if os.name == 'nt' and os.environ.get('LOCALAPPDATA') else None
        with BrowserTemporaryDirectory(dir=browser_temp) as tmp:
            root = Path(tmp)
            path = root / 'viewer.html'
            path.write_text(page, encoding='utf-8')
            driver = root / 'check-viewer.mjs'
            # dump-dom의 가상시간/자동종료 대신 DOM 완료 신호와 Browser.close를 사용한다.
            # Chrome에 파이프를 상속하지 않아 Windows 하위 프로세스가 communicate를 붙잡지 않는다.
            driver.write_text(r'''
import {spawn} from 'node:child_process';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
if(typeof WebSocket!=='function'||typeof fetch!=='function')throw Error('This CDP test requires Node with built-in WebSocket and fetch (Node 22+)');
const [chrome, file, profile] = process.argv.slice(2);
const content=await readFile(file);
const server=http.createServer((_request,response)=>{response.setHeader('Content-Type','text/html; charset=utf-8');response.end(content)});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url=`http://127.0.0.1:${server.address().port}/viewer.html`;
const browser = spawn(chrome, ['--headless=new', '--remote-debugging-port=0', '--no-first-run',
  '--no-default-browser-check', '--user-data-dir='+profile, 'about:blank'], {windowsHide:true, stdio:'ignore'});
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
let socket, command, sessionId;
const trace=[];
try {
  let port;
  const started=Date.now();
  while(Date.now()-started<15000) {
    try { port=(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break; }
    catch { if(browser.exitCode!==null)throw Error('Chrome exited before CDP was ready');await delay(100); }
  }
  if(!port)throw Error('Chrome did not publish DevToolsActivePort');
  const version=await (await fetch(`http://127.0.0.1:${port}/json/version`,{signal:AbortSignal.timeout(5000)})).json();
  socket=new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('CDP connect timed out')),5000);
    socket.onopen=()=>{clearTimeout(timer);resolve()};socket.onerror=error=>{clearTimeout(timer);reject(error)};
  });
  let next=0;
  const pending=new Map();
  socket.onmessage=event=>{
    const reply=JSON.parse(event.data), waiter=pending.get(reply.id);
    if(waiter){pending.delete(reply.id);clearTimeout(waiter.timer);trace.push({received:waiter.method});reply.error?waiter.reject(Error(JSON.stringify(reply.error))):waiter.resolve(reply.result)}
  };
  command=(method,params={})=>new Promise((resolve,reject)=>{
    trace.push({sent:method});
    const id=++next,timer=setTimeout(()=>{pending.delete(id);reject(Error(method+' timed out'))},15000);
    pending.set(id,{resolve,reject,timer,method});
    const session=sessionId&&!method.startsWith('Target.')&&!method.startsWith('Browser.')?{sessionId}:{};
    socket.send(JSON.stringify({id,method,params,...session}));
  });
  const target=await command('Target.createTarget',{url:'about:blank'});
  sessionId=(await command('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
  await command('Page.enable');await command('Runtime.enable');await command('Accessibility.enable');
  await command('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await command('Page.navigate',{url});
  let loaded=false;
  const opened=Date.now();
  while(Date.now()-opened<10000) {
    const reply=await command('Runtime.evaluate',{expression:"document.readyState==='complete' && typeof window.runGXViewerChecks==='function'",returnByValue:true});
    if(reply.exceptionDetails)throw Error(JSON.stringify(reply.exceptionDetails));
    if(reply.result.value){loaded=true;break}
    await delay(100);
  }
  if(!loaded)throw Error('Viewer did not finish initial navigation');
  // load 이벤트에서 hash를 바꾸면 첫 Page.navigate 응답과 중첩된다. 로드 후 별도 호출한다.
  const checked=await command('Runtime.evaluate',{expression:'window.runGXViewerChecks()',awaitPromise:true,returnByValue:true});
  if(checked.exceptionDetails)throw Error(JSON.stringify(checked.exceptionDetails));
  process.stdout.write(JSON.stringify(checked.result.value));
} catch(error) {
  process.stderr.write(JSON.stringify({trace,error:String(error)})+'\n');throw error;
} finally {
  if(command)await command('Browser.close').catch(()=>{});
  socket?.close();
  const closing=Date.now();
  while(browser.exitCode===null&&Date.now()-closing<3000)await delay(50);
  if(browser.exitCode===null){browser.kill();await new Promise(resolve=>{browser.once('exit',resolve);setTimeout(resolve,1000)})}
  server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
}
''', encoding='utf-8')
            artifacts = os.environ.get('GX_VIEWER_TEST_ARTIFACT_DIR')
            if artifacts:
                artifact_dir = Path(artifacts)
                artifact_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, artifact_dir / 'viewer.html')
                shutil.copyfile(driver, artifact_dir / 'check-viewer.mjs')
            run = subprocess.run([node, str(driver), chrome, str(path), str(root / 'profile')],
                                 capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=75)
            if artifacts:
                (artifact_dir / 'browser-stdout.json').write_text(run.stdout, encoding='utf-8')
                (artifact_dir / 'browser-stderr.log').write_text(run.stderr, encoding='utf-8')
        self.assertEqual(0, run.returncode, run.stderr[-2000:])
        result = json.loads(run.stdout)
        self.assertEqual(11, len(result))
        self.assertTrue(all(item['ok'] for item in result), result)

    def test_deleted_only_change_is_not_no_change(self):
        ir = document()
        ir['meta']['changes'] = {'available': True, 'removed': [{'id': 'old', 'label': '삭제된 API'}], 'removed_edges': ['edge-old'], 'base_ref': 'main'}
        html = self.fallback.change_banner_html(ir)
        self.assertIn('삭제 1개', html)
        self.assertIn('삭제된 관계 1개', html)
        self.assertIn('삭제된 API', html)
        self.assertNotIn('구조 변경이 없습니다', html)

    def test_missing_asset_is_table_and_present_asset_enables_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'ir.json'
            path.write_text(json.dumps(document()), encoding='utf-8')
            result = self.fallback.render(path, root, 'mermaid', mermaid_asset_href='mermaid.js')
            receipt = json.loads(Path(result['receipt_path']).read_text(encoding='utf-8'))
            self.assertEqual('table', receipt['capability'])
            self.assertNotIn('<pre class="mermaid">', Path(result['html_path']).read_text(encoding='utf-8'))
            (root / 'mermaid.js').write_text('/* deliberately broken JS for browser recovery */', encoding='utf-8')
            result = self.fallback.render(path, root, 'mermaid', mermaid_asset_href='mermaid.js')
            receipt = json.loads(Path(result['receipt_path']).read_text(encoding='utf-8'))
            self.assertEqual('diagram', receipt['capability'])
            self.assertEqual('browser', receipt['diagram_runtime'])
            html = Path(result['html_path']).read_text(encoding='utf-8')
            self.assertIn('그림을 표시하지 못했습니다', html)
            self.assertIn('목록으로 보기', html)
            self.assertIn('max-width:none!important', html)

    def test_remote_urls_drop_secrets_and_reject_local_origins(self):
        for remote in ['C:/repo', '/tmp/repo', '../repo', 'file:///repo', 'git://example/repo']:
            self.assertIsNone(self.archify._supported_remote(remote))
        self.assertEqual('https://example.com/org/repo.git', self.archify._supported_remote('https://token:secret@example.com/org/repo.git?token=secret#private'))
        self.assertEqual('git@example.com:org/repo.git', self.archify._supported_remote('git@example.com:org/repo.git'))

    @unittest.skipUnless(shutil.which('git'), 'git required')
    def test_module_evidence_uses_repository_top_level_without_mutating_ir(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            subprocess.run(['git', 'init', '-q'], cwd=top, check=True)
            module = top / 'modules/users'
            module.mkdir(parents=True)
            ir = document()
            ir['nodes'][0]['evidence'] = [{'kind': 'code', 'file': 'src/User.java', 'line': 1}]
            root, mapped = self.archify._repository_context(module, ir)
            self.assertEqual(top.resolve(), root)
            self.assertEqual('modules/users/src/User.java', mapped['nodes'][0]['evidence'][0]['file'])
            self.assertEqual('src/User.java', ir['nodes'][0]['evidence'][0]['file'])


if __name__ == '__main__':
    unittest.main()
