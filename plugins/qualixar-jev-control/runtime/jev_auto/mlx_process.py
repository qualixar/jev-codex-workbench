"""Persistent isolated Python worker. Pipes never carry cloud credentials."""
from __future__ import annotations
import os, selectors, subprocess, sys, threading, time
from pathlib import Path
from .common import AutoError, canonical, decode, safe_path

class MLXProcess:
    def __init__(self,cfg):
        self.cfg=cfg;self.proc=None;self.lock=threading.Lock();self.buf=b''
    def _start(self):
        python=Path(self.cfg['python']).expanduser()
        if not python.is_file():raise AutoError('MLX_PYTHON_MISSING')
        env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('KEY','TOKEN','PASSWORD','SECRET'))}
        env.update({'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PYTHONDONTWRITEBYTECODE':'1',
                    'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
        self.proc=subprocess.Popen([str(python),'-m','jev_auto.mlx_worker'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL,env=env,bufsize=0)
        self.buf=b''
        self._exchange({'kind':'load','config':self.cfg},120)
    def _exchange(self,obj,timeout):
        p=self.proc
        if p is None or p.poll() is not None:raise AutoError('MLX_WORKER_STOPPED')
        p.stdin.write(canonical(obj)+b'\n');p.stdin.flush();deadline=time.monotonic()+timeout
        with selectors.DefaultSelector() as sel:
            sel.register(p.stdout,selectors.EVENT_READ)
            while b'\n' not in self.buf:
                if not sel.select(max(0,deadline-time.monotonic())):raise AutoError('MLX_WORKER_TIMEOUT')
                part=os.read(p.stdout.fileno(),65536)
                if not part:raise AutoError('MLX_WORKER_STOPPED')
                self.buf+=part
                if len(self.buf)>1_000_000:raise AutoError('MLX_WORKER_RESPONSE_SIZE')
        line,self.buf=self.buf.split(b'\n',1);result=decode(line,1_000_000)
        if not result.get('ok'):raise AutoError(result.get('error','MLX_WORKER_ERROR'))
        return result['result']
    def warmup(self):
        with self.lock:
            if self.proc is None:self._start()
        return {'ready':True,'provider':'laya-mlx'}
    def predict(self,state,questions,timeout):
        with self.lock:
            if self.proc is None:
                raise AutoError('MLX_WARMUP_REQUIRED')
            try:return self._exchange({'kind':'predict','state':state,'questions':questions},timeout)
            except AutoError as error:
                if not str(error).startswith(('MLX_OPTION_WOULD_', 'MLX_RUBRIC_WOULD_', 'MLX_INSTRUCTIONS_WOULD_', 'MLX_STATE_WOULD_')):
                    self.close()
                raise
    def close(self):
        if self.proc:
            self.proc.terminate()
            try:self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()
            if self.proc.stdin:self.proc.stdin.close()
            if self.proc.stdout:self.proc.stdout.close()
            self.proc=None
