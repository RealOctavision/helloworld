"""Local-only CPU inference over public, fixed PPI replay samples. No training/capture."""
import argparse,json,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import urlparse,parse_qs
import numpy as np
import torch
import lightgbm as lgb
from data import HERE,ROOT,digest,read_split,write_json
from colab_main import frozen_config
from models import make_model,statistics
from training import load_checkpoint

class Demo:
    def __init__(self,kinds=None):
        wanted=set(kinds or ['M0','M1','M2','M3','M4','M5'])
        if not wanted or not wanted.issubset({'M0','M1','M2','M3','M4','M5'}):raise ValueError('Unknown model')
        self.cfg,self.f=frozen_config();self.classes=self.cfg['cohorts'][self.f['cohort']]['classes']
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        registry=json.loads((HERE/'main_recovered/training_registry.json').read_text())
        training=json.loads((ROOT/registry['verification']).read_text())
        if not training['verified']or training['completed']!=30:raise ValueError('Verified representative training required')
        self.models={};self.checkpoints={};self.samples={};self.indices={}
        for r in training['records']:
            if r['seed']!=201 or r['model']not in wanted:continue
            kind=r['model'];cp=ROOT/r['checkpoint']
            if digest(cp)!=r['checkpoint_sha256']:raise ValueError('Checkpoint changed')
            if kind=='M0':model=lgb.Booster(model_file=str(cp))
            else:
                model=make_model(kind,len(self.classes),201,self.cfg,load_pretrained=False);load_checkpoint(cp,model);model.eval()
            self.models[kind]=model;self.checkpoints[kind]=digest(cp)
        for month in ['202504','202505']:
            d=read_split(self.f['cohort'],f'evaluation_{month}');rng=np.random.default_rng(20261031)
            indices=np.concatenate([rng.permutation(np.flatnonzero(d['y']==i))[:3]for i in range(len(self.classes))]);indices=rng.permutation(indices)
            self.indices[month]=indices;self.samples[month]={k:d[k][indices].copy()for k in ['X','y','id']}
        if set(self.models)!=wanted:raise ValueError('Missing demo models')
    def predict(self,month,index):
        if month not in self.samples or not 0<=index<len(self.samples[month]['y']):raise ValueError('Unknown fixed sample')
        d=self.samples[month];x=d['X'][index:index+1];xt=torch.as_tensor(x,dtype=torch.float32);rows=[]
        with torch.inference_mode():
            for kind in sorted(self.models):
                t=time.perf_counter()
                prob=self.models[kind].predict(statistics(x)[0],num_threads=1)[0]if kind=='M0'else self.models[kind](xt).softmax(1)[0].numpy()
                elapsed=(time.perf_counter()-t)*1000
                if not np.isfinite(prob).all():raise ValueError('Nonfinite prediction')
                top=np.argsort(-prob)[:3]
                rows.append(dict(model=kind,predicted=int(top[0]),top3=[dict(service=self.classes[i],probability=float(prob[i]))for i in top],elapsed_ms=elapsed,checkpoint_sha256=self.checkpoints[kind]))
        valid=x[0,1]!=0
        return dict(month=month,index=index,total=len(d['y']),source_id=str(d['id'][index]),truth=self.classes[int(d['y'][index])],truth_index=int(d['y'][index]),
            valid_packets=int(valid.sum()),ppi=x[0].tolist(),channel_order=['IPT(ms)','direction','size(bytes)'],models=rows,
            scope='Fixed public PPI replay; real CPU inference, no live packet capture, training, or teacher input to student. Single-call timing is not a benchmark.')
    def verify(self):
        reg=json.loads((HERE/'main_recovered/evaluation_registry.json').read_text());ev=json.loads((ROOT/reg['verification']).read_text())
        checked=[]
        for month in ['202504','202505']:
            for index in [0,1,2]:
                result=self.predict(month,index);original=int(self.indices[month][index])
                for row in result['models']:
                    r=next(r for r in ev['records']if r['month']==month and r['model']==row['model']and r['seed']==201)
                    with np.load(ROOT/r['prediction_path'],allow_pickle=False)as z:
                        if int(z['predicted_label'][original])!=row['predicted']:raise ValueError('CPU replay differs from recorded label')
                    checked.append(dict(month=month,index=index,original_row=original,model=row['model'],prediction=row['predicted']))
        report=dict(passed=True,source_sha256=digest(Path(__file__)),checked_predictions=len(checked),checks=checked,seed=201,budget=200,
            checkpoint_sha256=self.checkpoints,scope='Six fixed replay samples × six models, CPU predictions match recorded evaluation labels. No live capture or new fitting; not whole-dataset bitwise equivalence.')
        write_json(HERE/'cpu_demo_verification.json',report);print(json.dumps({k:report[k]for k in ['passed','checked_predictions','scope']}))
        return report

HTML='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>30-PPI CPU 분류 시연</title><style>
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f4f6f8;color:#182b3c;margin:0}main{max-width:1100px;margin:auto;padding:36px}h1{font-size:32px;margin-bottom:10px}p{line-height:1.7}.sub{color:#536477}section{background:white;padding:24px;margin:20px 0;border:1px solid #d7dfe5}button,select,input{font:inherit;padding:9px;margin:4px}button{background:#163c5c;color:white;border:0;cursor:pointer}button:disabled{opacity:.5}table{border-collapse:collapse;width:100%;margin-top:15px}th,td{padding:12px;border-bottom:1px solid #dce3e8;text-align:left}th{background:#f4f6f8}.right{color:#11613f}.wrong{color:#933331}pre{overflow:auto;background:#f5f7f9;padding:16px;font-size:12px}.big{font-size:22px;font-weight:650}small{color:#5d6d7c}#error{color:#933331}</style>
<main><h1>첫 최대30패킷으로 서비스 분류</h1><p class="sub">공개 평가 PPI를 재생해 선택한 검증 모델이 이 Mac의 CPU에서 직접 추론합니다.<br>대표 Google 포함20 · 클래스당200개 학습 · 미리 고정한 seed201 · 서비스당3개 고정 무작위 시연 표본</p>
<section><label>평가월 <select id="month"><option value="202504">2025년4월</option><option value="202505">2025년5월</option></select></label><label>표본번호 <input id="index" type="number" min="0" max="59" value="0" style="width:75px"></label><button id="run">CPU에서 분류</button><button id="next">다음 표본</button><label><input type="checkbox" id="showtruth"> 실제 정답 표시</label><p id="error" role="alert"></p><p id="sample" class="big">분류 버튼을 눌러 시작하세요.</p><p id="truth" hidden></p><table><thead><tr><th>모델</th><th>1순위 예측</th><th>확률</th><th>2·3순위</th><th>이번 연산(ms)</th></tr></thead><tbody id="results"></tbody></table></section>
<section><h2>입력과 해석 범위</h2><p>모델 입력은 패킷 간격(IPT), 방향, 크기입니다. 실제 정답·교사 예측은 학생의 추론 입력에 넣지 않습니다. 각 모델은 독립적으로 같은 PPI를 처리합니다.</p><p>저장된 플로우 재생이며 실제 네트워크 패킷을 수집하는 시연은 아닙니다. 한 번의 연산 시간에는 초기 실행 영향이 있으므로 정식 CPU 벤치마크 표와 구분합니다. 출력은 등록된20서비스 중 하나이며 미등록 서비스·이상 탐지 기능은 포함하지 않습니다.</p><details><summary>현재 표본의 PPI 보기</summary><pre id="ppi">입력 전</pre></details></section></main>
<script>let latest=null;const $=id=>document.getElementById(id);function truth(){if(!latest)return;$('truth').hidden=!$('showtruth').checked;$('truth').textContent='실제 정답: '+latest.truth;for(const tr of $('results').children){tr.className=$('showtruth').checked?(tr.dataset.correct==='true'?'right':'wrong'):'';}}async function run(){if($('run').disabled)return;$('run').disabled=true;$('next').disabled=true;$('error').textContent='';try{let index=Number($('index').value);if(!Number.isInteger(index)||index<0||index>59)throw Error('표본번호는0~59 정수입니다.');let r=await fetch('/api/predict?month='+$('month').value+'&index='+index);let d=await r.json();if(!r.ok)throw Error(d.error);latest=d;$('sample').textContent='표본 '+d.index+' / 유효패킷 '+d.valid_packets+'개';$('ppi').textContent=JSON.stringify({id:d.source_id,channel_order:d.channel_order,ppi:d.ppi},null,2);$('results').replaceChildren();for(let row of d.models){let tr=document.createElement('tr');tr.dataset.correct=String(row.predicted===d.truth_index);for(let value of [row.model,row.top3[0].service,(row.top3[0].probability*100).toFixed(2)+'%',row.top3.slice(1).map(t=>t.service+' '+(t.probability*100).toFixed(1)+'%').join(' / '),row.elapsed_ms.toFixed(3)]){let td=document.createElement('td');td.textContent=value;tr.append(td);}$('results').append(tr);}truth();}catch(e){$('error').textContent=e.message;}finally{$('run').disabled=false;$('next').disabled=false;}}$('run').onclick=run;$('next').onclick=()=>{$('index').value=(Number($('index').value)+1)%60;run();};$('showtruth').onchange=truth;</script></html>'''

def serve(demo,port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host')not in [f'127.0.0.1:{port}',f'localhost:{port}']:
                self.send_error(403);return
            path=urlparse(self.path)
            try:
                if path.path=='/':content=HTML.encode();mime='text/html; charset=utf-8'
                elif path.path=='/api/predict':
                    q=parse_qs(path.query);content=json.dumps(demo.predict(q.get('month',['202504'])[0],int(q.get('index',['0'])[0])),ensure_ascii=False).encode();mime='application/json; charset=utf-8'
                else:self.send_error(404);return
                self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(content)
            except (ValueError,KeyError)as e:
                content=json.dumps({'error':str(e)}).encode();self.send_response(400);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(content)
        def log_message(self,fmt,*args):print(fmt%args,flush=True)
    server=HTTPServer(('127.0.0.1',port),Handler)
    print(f'DEMO_READY http://127.0.0.1:{port}',flush=True)
    server.serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--port',type=int,default=8768);p.add_argument('--models',default='M0,M1,M2,M3,M4,M5');a=p.parse_args();d=Demo(a.models.split(','))
    if a.verify:d.verify()
    else:serve(d,a.port)
