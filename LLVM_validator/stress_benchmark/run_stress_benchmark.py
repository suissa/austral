#!/usr/bin/env python3
import json, os, socket, subprocess, time, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_SRC = (ROOT / "../../examples/llvm_linear_api/linear_token_api.c").resolve()
OUT = ROOT


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{p.stderr}")
    return p


def build_artifacts():
    c_bin = OUT / "linear_api_c"
    ll_file = OUT / "linear_api.ll"
    ll_bin = OUT / "linear_api_llvm"
    run(["cc", str(API_SRC), "-O3", "-o", str(c_bin)])
    run(["clang", "-S", "-emit-llvm", str(API_SRC), "-O3", "-o", str(ll_file)])
    run(["clang", str(ll_file), "-O3", "-o", str(ll_bin)])
    return c_bin, ll_bin


def wait_server(port):
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("server did not start")


def call_once(port, payload):
    t0 = time.perf_counter()
    with socket.create_connection(("127.0.0.1", port), timeout=2.0) as s:
        s.sendall(("TOKEN " + payload + "\n").encode())
        _ = s.recv(256)
    return (time.perf_counter() - t0) * 1000.0


def run_profile(bin_path, port, duration_s=30, stage_s=2):
    proc = subprocess.Popen([str(bin_path), str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        wait_server(port)
        start = time.time()
        qps = 1024 * 1024
        stages = []
        while time.time() - start < duration_s:
            lat = []
            t_stage = time.time()
            count = 0
            while time.time() - t_stage < stage_s:
                lat.append(call_once(port, f"payload-{count}-{qps}"))
                count += 1
            elapsed = time.time() - t_stage
            stages.append({
                "target_qps": qps,
                "actual_calls": count,
                "elapsed_s": elapsed,
                "throughput_cps": count / elapsed if elapsed else 0,
                "p50_ms": statistics.median(lat) if lat else 0,
                "p95_ms": sorted(lat)[int(0.95 * (len(lat)-1))] if lat else 0,
                "max_ms": max(lat) if lat else 0,
            })
            qps *= 2
        return stages
    finally:
        proc.kill()
        proc.wait(timeout=2)


def html_report(stress, bench):
    html = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<script src='https://cdn.tailwindcss.com'></script><title>Tests Report</title></head>
<body class='bg-slate-950 text-slate-100 p-6'>
<h1 class='text-2xl font-bold mb-4'>Stress & Benchmark Report</h1>
<div class='grid grid-cols-1 md:grid-cols-2 gap-4'>
  <button onclick='openModal("stress")' class='text-left rounded-xl p-4 bg-slate-800 hover:bg-slate-700'><h2 class='text-xl font-semibold'>Stress Test</h2><p>1Mi calls baseline, doubling each 2s for 30s.</p></button>
  <button onclick='openModal("bench")' class='text-left rounded-xl p-4 bg-slate-800 hover:bg-slate-700'><h2 class='text-xl font-semibold'>Benchmark C vs LLVM</h2><p>Latency and throughput comparison.</p></button>
</div>
<div id='modal' class='hidden fixed inset-0 bg-black/70 items-center justify-center'><div class='bg-slate-900 w-11/12 max-w-5xl rounded-xl p-4'>
<button class='float-right bg-slate-700 px-3 py-1 rounded' onclick='closeModal()'>fechar</button><h3 id='mtitle' class='text-xl mb-3'></h3>
<pre id='telemetry' class='bg-slate-800 p-3 rounded max-h-64 overflow-auto'></pre>
<canvas id='chart' width='900' height='300' class='mt-4 bg-white rounded'></canvas>
</div></div>
<script>
const DATA = {json.dumps({'stress': stress, 'bench': bench})};
function draw(values, label){{
 const c = document.getElementById('chart'); const ctx = c.getContext('2d');
 ctx.clearRect(0,0,c.width,c.height); ctx.fillStyle='#111827'; ctx.fillRect(0,0,c.width,c.height);
 const max=Math.max(...values,1); const w=(c.width-40)/values.length;
 ctx.fillStyle='#22d3ee'; values.forEach((v,i)=>{{const h=(v/max)*(c.height-40); ctx.fillRect(20+i*w,c.height-20-h,w-4,h);}});
 ctx.fillStyle='white'; ctx.fillText(label,20,20);
}}
function openModal(kind){{
 document.getElementById('modal').classList.remove('hidden'); document.getElementById('modal').classList.add('flex');
 const d=DATA[kind]; document.getElementById('mtitle').textContent = kind==='stress' ? 'Stress Telemetry' : 'Benchmark Telemetry';
 document.getElementById('telemetry').textContent = JSON.stringify(d,null,2);
 if(kind==='stress') draw(d.c.map(s=>s.throughput_cps), 'C throughput by stage');
 else draw([d.summary.c_avg_ms,d.summary.llvm_avg_ms], 'Average latency ms (C vs LLVM)');
}}
function closeModal(){{document.getElementById('modal').classList.add('hidden');document.getElementById('modal').classList.remove('flex')}}
</script></body></html>"""
    (OUT / "tests_report.html").write_text(html)


def main():
    c_bin, ll_bin = build_artifacts()
    stress = {
      "type": "stress_test",
      "started_at": int(time.time()),
      "config": {"initial_calls": 1024*1024, "double_every_s": 2, "duration_s": 30},
      "c": run_profile(c_bin, 9091),
      "llvm": run_profile(ll_bin, 9092)
    }
    (OUT / "stress_test.json").write_text(json.dumps(stress, indent=2))

    # fresh servers for benchmark
    p1 = subprocess.Popen([str(c_bin), "9093"])
    wait_server(9093)
    lat_c = [call_once(9093, f"bench-{i}") for i in range(200)]
    p1.kill(); p1.wait()

    p2 = subprocess.Popen([str(ll_bin), "9094"])
    wait_server(9094)
    lat_l = [call_once(9094, f"bench-{i}") for i in range(200)]
    p2.kill(); p2.wait()

    bench = {
      "type": "benchmark_test",
      "samples": 200,
      "c_latency_ms": lat_c,
      "llvm_latency_ms": lat_l,
      "summary": {
        "c_avg_ms": statistics.mean(lat_c),
        "llvm_avg_ms": statistics.mean(lat_l),
        "c_p95_ms": sorted(lat_c)[189],
        "llvm_p95_ms": sorted(lat_l)[189]
      }
    }
    (OUT / "benchmark_test.json").write_text(json.dumps(bench, indent=2))
    html_report(stress, bench)
    print("Generated stress_test.json, benchmark_test.json, tests_report.html")

if __name__ == '__main__':
    main()
