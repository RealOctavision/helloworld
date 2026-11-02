import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {marked} from '/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/marked/lib/marked.esm.js';
const dir=path.dirname(fileURLToPath(import.meta.url));
const markdown=fs.readFileSync(path.join(dir,'report.md'),'utf8');
// Korean suffixes after symbols such as % can prevent CommonMark strong parsing.
const prepared=markdown.split(/(```[\s\S]*?```)/g).map((part,i)=>i%2?part:part.replace(/\*\*([^\n]+?)\*\*/g,'<strong>$1</strong>')).join('');
let body=marked.parse(prepared,{gfm:true});
const toc=[];let seq=0;
body=body.replace(/<h([23])>(.*?)<\/h\1>/gs,(_,level,title)=>{
 const id=`s${++seq}`;
 if(level==='2')toc.push({id,title:title.replace(/<[^>]*>/g,'')});
 return `<h${level} id="${id}">${title}</h${level}>`;
});
body=body.replace(/<table>/g,'<div class="table-wrap" tabindex="0" role="region" aria-label="좌우로 스크롤할 수 있는 표"><table>').replace(/<\/table>/g,'</table></div>');
body=body.replace(/src="figures\/([^"/]+\.svg)"/g,(_,name)=>`src="data:image/svg+xml;base64,${fs.readFileSync(path.join(dir,'figures',name)).toString('base64')}"`);
const evidence=fs.readFileSync(path.join(dir,'report_data.json'),'utf8').replaceAll('<','\\u003c');
const css=fs.readFileSync(path.join(dir,'style.css'),'utf8');
const escaped=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const nav=toc.map((x,i)=>`<a href="#${x.id}" ${i>=11?'class="appendix-link"':''}><span>${i<11?String(i+1).padStart(2,'0'):String.fromCharCode(65+i-11)}</span>${escaped(x.title.replace(/^\d+\.\s*|^부록 [A-F]\.\s*/g,''))}</a>`).join('');
const document=`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="CESNET QUIC 트래픽 분류의 데이터 처리, M0–M5 모델, 180회 학습, 성능·비용 결과와 재현 근거"><title>암호화 트래픽 분류 · 중간발표 실험 보고서</title><style>${css}</style></head><body><a class="skip-link" href="#report">본문으로 이동</a><aside><a class="brand" href="#top"><span>CAPSTONE RESEARCH</span><b>실험 보고서</b><small>30-PPI · 전이학습 · 지식 증류</small></a><div class="sidebar-actions"><button id="print" title="본문과 부록을 모두 펼쳐 인쇄">인쇄 / PDF</button><button id="expand">부록 펼치기</button></div><nav aria-label="보고서 목차">${nav}</nav><div class="sidebar-foot">2026.10.31 · 검증된 실험 결과<br>본문11장 · 상세부록6개<br>그래프·표는 이 HTML에 포함</div></aside><div class="mobile-bar"><b>중간발표 실험 보고서</b><button id="mobile-menu" aria-expanded="false">목차</button></div><main id="report"><div id="top"></div><article>${body}</article><footer><strong>이 문서의 기준</strong><p>현재 고정 설계의 검증된 결과를 바탕으로 작성했다. 관찰·해석·미측정을 구분하며 원본 자료를 대체하지 않는다. 도표는 HTML 안에 포함되어 오프라인에서도 읽을 수 있다. 원본 근거 링크는 프로젝트 폴더와 함께 보관할 때 사용할 수 있다.</p><p><a href="#top">처음으로 ↑</a> · <button class="inline-button" id="export-markdown">보고서 Markdown 저장</button></p></footer></main><dialog id="figure-dialog"><button id="close-figure" aria-label="확대 그림 닫기">닫기 ×</button><img alt="확대한 보고서 그래프"></dialog><script type="application/json" id="report-data">${evidence}</script><script type="application/json" id="report-markdown">${JSON.stringify(fs.readFileSync(path.join(dir,'report.md'),'utf8')).replaceAll('<','\\u003c')}</script><script>
const details=[...document.querySelectorAll('details')];
const expand=document.getElementById('expand');
expand.addEventListener('click',()=>{const open=details.some(d=>!d.open);details.forEach(d=>d.open=open);expand.textContent=open?'부록 접기':'부록 펼치기'});
document.getElementById('print').addEventListener('click',()=>{details.forEach(d=>d.open=true);window.print()});
window.addEventListener('beforeprint',()=>details.forEach(d=>d.open=true));
const menu=document.getElementById('mobile-menu');
menu.addEventListener('click',()=>{const open=document.body.classList.toggle('menu-open');menu.setAttribute('aria-expanded',String(open))});
document.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',()=>{document.body.classList.remove('menu-open');menu.setAttribute('aria-expanded','false')}));
function download(name,value,type){const url=URL.createObjectURL(new Blob([value],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
document.getElementById('export-data').addEventListener('click',()=>download('midterm_report_data.json',document.getElementById('report-data').textContent,'application/json'));
document.getElementById('export-markdown').addEventListener('click',()=>download('midterm_report.md',JSON.parse(document.getElementById('report-markdown').textContent),'text/markdown'));
const dialog=document.getElementById('figure-dialog');
document.querySelectorAll('figure img').forEach(img=>{img.tabIndex=0;img.setAttribute('role','button');img.setAttribute('aria-label',img.alt+' 확대');const show=()=>{dialog.querySelector('img').src=img.src;dialog.querySelector('img').alt=img.alt;dialog.showModal()};img.addEventListener('click',show);img.addEventListener('keydown',e=>{if(e.key==='Enter'){show()}})});
document.getElementById('close-figure').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});
const anchors=[...document.querySelectorAll('nav a')];
const observe=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){anchors.forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))}},{rootMargin:'-10% 0px -70% 0px'});
document.querySelectorAll('h2').forEach(h=>observe.observe(h));
</script></body></html>`;
fs.writeFileSync(path.join(dir,'report.html'),document);
console.log(JSON.stringify({htmlBytes:Buffer.byteLength(document),chapters:toc.length,embeddedFigures:(body.match(/data:image/g)||[]).length,externalImageCount:(body.match(/src="figures/g)||[]).length}));
