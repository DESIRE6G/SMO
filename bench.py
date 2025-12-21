#!/usr/bin/env python3
"""
SMO Benchmarking Script with CSV Export
Measures latency, throughput, and resource usage for different scaling configurations
Exports results to scaling_data.csv for visualization
"""

import requests
import time
import json
import subprocess
import statistics
import threading
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import sys
import os
import psutil
import re

# Configuration
SERVICE_ORCHESTRATOR_URL = "http://localhost:8000/services"
SERVICE_NAME = "demo1_nsd.sg.yml"
NUM_REQUESTS = 100
MAX_WORKERS = 8
MIN_WORKERS = 1


OE_TIME_RE = re.compile(
    r"Total handling time:\s*([0-9]+(?:\.[0-9]+)?)\s*milliseconds\.?",
    re.IGNORECASE
)

def percentiles(values, ps=(50, 90, 95, 99)):
    """
    Compute percentiles for a list of numbers.
    Returns dict: {p: value}
    """
    if not values:
        return {p: 0 for p in ps}

    values = sorted(values)
    n = len(values)

    out = {}
    for p in ps:
        k = (n - 1) * (p / 100)
        f = int(k)
        c = min(f + 1, n - 1)

        if f == c:
            out[p] = values[f]
        else:
            out[p] = values[f] * (c - k) + values[c] * (k - f)
    return out


def collect_oe_internal_times():
    """
    Inspect optimization-engine container logs and extract internal handling times (ms).
    """
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=optimization-engine", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )

    containers = [c.strip() for c in result.stdout.splitlines()]
    times = []

    for cname in containers:
        logs = subprocess.run(
            ["docker", "logs", cname],
            capture_output=True,
            text=True
        )
        for line in logs.stdout.splitlines() + logs.stderr.splitlines():
            match = OE_TIME_RE.search(line)
            if match:
                times.append(float(match.group(1)))

    return times


def get_container_id(container_name):
    """Return container ID from container name."""
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.Id}}", container_name],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def get_cgroup_path(container_id):
    """
    Locate cgroup v2 directory for a Docker container across different host setups.
    """
    candidates = [
        f"/sys/fs/cgroup/system.slice/docker-{container_id}.scope",
        f"/sys/fs/cgroup/docker/{container_id}",
        f"/sys/fs/cgroup/{container_id}",
        f"/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/docker-{container_id}.scope",
        f"/sys/fs/cgroup/system.slice/containerd-{container_id}.scope",
    ]

    for path in candidates:
        if os.path.isdir(path):
            return path

    try:
        for entry in os.listdir("/sys/fs/cgroup/system.slice"):
            if container_id in entry:
                scope_path = os.path.join("/sys/fs/cgroup/system.slice", entry)
                if os.path.isdir(scope_path):
                    return scope_path
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        f"cgroup v2 path not found for container {container_id}\n"
        f"Tried: {', '.join(candidates)}"
    )

def read_cpu_usage_usec(cgpath):
    """Read total CPU usage (microseconds) from cpu.stat."""
    with open(os.path.join(cgpath, "cpu.stat")) as f:
        for line in f:
            key, val = line.split()
            if key == "usage_usec":
                return int(val)
    return 0

def read_memory_current(cgpath):
    """Return memory usage in bytes."""
    with open(os.path.join(cgpath, "memory.current")) as f:
        return int(f.read().strip())

def send_deployment_request(exid: str, request: str):
    """Send a single deployment request and measure latency"""
    start_time = time.time()
    try:
        response = requests.post(
            SERVICE_ORCHESTRATOR_URL,
            json={"name": SERVICE_NAME},
            timeout=120
        )
        end_time = time.time()
        latency = end_time - start_time
        timings = response.json()['measure']
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "timings": timings,
            "latency": latency,
            "timestamp": start_time
        }
    except requests.exceptions.Timeout:
        end_time = time.time()
        return {
            "success": False,
            "status_code": "TIMEOUT",
            "timings": {},
            "latency": end_time - start_time,
            "timestamp": start_time
        }
    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "status_code": f"ERROR: {str(e)}",
            "timings": {},
            "latency": end_time - start_time,
            "timestamp": start_time
        }

def monitor_container_stats(stop_event, max_stats_dict):
    """
    Monitor cgroup-based CPU and memory for all SMO containers.
    """
    container_paths = {}
    prev_cpu_usage = {}
    prev_time = time.time()
    num_cpus = psutil.cpu_count(logical=True)

    try:
        while not stop_event.is_set():
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            container_names = [
                name.strip()
                for name in result.stdout.splitlines()+result.stderr.splitlines()
                if 'smo-' in name or 'compose-smo-' in name
            ]

            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt <= 0:
                dt = 0.1

            for cname in container_names:
                if cname not in container_paths:
                    cid = get_container_id(cname)
                    try:
                        container_paths[cname] = get_cgroup_path(cid)
                    except FileNotFoundError:
                        continue

                cgpath = container_paths[cname]

                cpu_now = read_cpu_usage_usec(cgpath)
                cpu_prev = prev_cpu_usage.get(cname, cpu_now)
                cpu_used_cores = (cpu_now - cpu_prev) / 1_000_000.0 / dt
                prev_cpu_usage[cname] = cpu_now
                cpu_percent = (cpu_used_cores / num_cpus) * 100
                if cpu_percent < 0:
                    cpu_percent = 0

                mem_bytes = read_memory_current(cgpath)
                mem_mib = mem_bytes / (1024 * 1024)

                #print(cname)
                if cname not in max_stats_dict:
                    max_stats_dict[cname] = {
                        'cpu': cpu_percent,
                        'memory_mib': mem_mib
                    }
                else:
                    max_stats_dict[cname]['cpu'] = max(
                        max_stats_dict[cname]['cpu'],
                        cpu_percent
                    )
                    max_stats_dict[cname]['memory_mib'] = max(
                        max_stats_dict[cname]['memory_mib'],
                        mem_mib
                    )


    except Exception as e:
        print(f"Warning: Error monitoring cgroup stats: {e}")

def scale_optimization_engine(num_instances):
    """Scale the optimization engine to specified number of instances"""
    print(f"\n🔧 Scaling Optimization Engine to {num_instances} instances...")

    subprocess.run(
        ['docker', 'compose', 'stop', 'smo-optimization-engine'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True
    )

    subprocess.run(
        ['docker', 'compose', 'rm', '-f', 'smo-optimization-engine'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True
    )

    result = subprocess.run(
        ['docker', 'compose', 'up', '-d', '--scale', f'smo-optimization-engine={num_instances}'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error scaling: {result.stderr}")
        return False

    print("⏳ Waiting for containers to initialize...")
    time.sleep(10)

    ps_result = subprocess.run(
        ['docker', 'compose', 'ps'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True,
        text=True
    )

    running_count = sum(1 for line in ps_result.stdout.split('\n')
                       if 'optimization-engine' in line and 'Up' in line)

    if running_count == 0:
        print(f"⚠️  Warning: 0 instances detected.")
        direct_check = subprocess.run(
            ['docker', 'ps', '--filter', 'name=optimization-engine', '--format', '{{.Names}}'],
            capture_output=True,
            text=True
        )
        print(f"   Direct docker ps found: {direct_check.stdout.strip()}")
    else:
        print(f"✅ {running_count} OE instances running")

    return running_count == num_instances

def run_benchmark(num_requests=NUM_REQUESTS, num_workers=MAX_WORKERS):
    """Run benchmark with specified parameters"""
    print(f"\n📊 Starting benchmark: {num_requests} requests with {num_workers} concurrent workers")
    print(f"🕐 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    stop_monitoring = threading.Event()
    max_stats = {}
    monitor_thread = threading.Thread(
        target=monitor_container_stats,
        args=(stop_monitoring, max_stats),
        daemon=True
    )

    overall_start = time.time()
    monitor_thread.start()

    results = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(send_deployment_request, executor, request) 
                  for request in range(num_requests)]

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)

            if i % 100 == 0:
                print(f"  Progress: {i}/{num_requests} requests completed")

    overall_end = time.time()
    overall_duration = overall_end - overall_start

    oe_internal_times = collect_oe_internal_times()
    stop_monitoring.set()
    monitor_thread.join(timeout=5)

    # Format stats
    final_stats = {}
    for container_name, stats in max_stats.items():
        final_stats[container_name] = {
            'cpu': stats['cpu'],  # Keep as float for CSV
            'memory_mib': stats['memory_mib']
        }

    # Calculate metrics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    latencies = [r['latency'] for r in results]
    timings = [r['timings'] for r in results]

    print(f"Failed:                  {len(failed)} ({len(failed)/num_requests*100:.1f}%)")
    # Parse timing components
    sc_list, mq_list, oe_list, deploy_list, totals = [], [], [], [], []
    for entry in timings:
        sc_list.append(entry['sc'])
        mq_list.append(entry['mq'])
        oe_list.append(entry['OE'])
        deploy_total = sum(d['site_retrieve'] + d['deploy'] for d in entry['deploy'])
        deploy_list.append(deploy_total)
        total = entry['sc'] + entry['mq'] + entry['OE'] + deploy_total
        totals.append(total)

    mq_p = percentiles(mq_list)
    oe_int_p = percentiles(oe_internal_times)


    def stats(lst):
        return {
            'avg': sum(lst)/len(lst) if lst else 0,
            'min': min(lst) if lst else 0,
            'max': max(lst) if lst else 0
        }

    results_total = {
        'sc': stats(sc_list),
        'mq': stats(mq_list),
        'OE': stats(oe_list),
        'deploy': stats(deploy_list),
        'totals': stats(totals)
    }

    print(f"\n{'='*60}")
    print(f"📈 BENCHMARK RESULTS")
    print(f"{'='*60}")
    print(f"Total requests:          {num_requests}")
    print(f"Successful:              {len(successful)} ({len(successful)/num_requests*100:.1f}%)")
    print(f"Failed:                  {len(failed)} ({len(failed)/num_requests*100:.1f}%)")
    print(f"\n⏱️  TIMING METRICS")
    print(f"Total duration:          {overall_duration:.2f}s")
    print(f"Throughput:              {num_requests/overall_duration:.2f} requests/sec")
    print(f"Average latency:         {statistics.mean(latencies):.2f}s")
    print(f"Median latency:          {statistics.median(latencies):.2f}s")
    print(f"Min latency:             {min(latencies):.2f}s")
    print(f"Max latency:             {max(latencies):.2f}s")
    if len(latencies) > 1:
        print(f"Std deviation:           {statistics.stdev(latencies):.2f}s")

    print(f"\n💻 RESOURCE USAGE (Peak values during test)")
    for container_name in sorted(final_stats.keys()):
        stats_entry = final_stats[container_name]
        print(f"{container_name:40s} Peak CPU: {stats_entry['cpu']:>7.2f}%  MEM: {stats_entry['memory_mib']}")

    print(f"{'='*60}\n")

    return {
        'num_requests': num_requests,
        'successful': len(successful),
        'failed': len(failed),
        'total_duration': overall_duration,
        'oe_internal_times': oe_internal_times,
        'throughput': num_requests/overall_duration,
        'avg_latency': statistics.mean(latencies),
        'median_latency': statistics.median(latencies),
        'min_latency': min(latencies),
        'max_latency': max(latencies),
        'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
        'resource_stats': final_stats,
        'results_total': results_total,
        'mq_percentiles': mq_p,              
        'oe_internal_percentiles': oe_int_p,  

    }

def export_to_csv(comparison_results, output_file='scaling_data.csv'):
    """Export benchmark results to CSV for plotting"""
    print(f"\n📄 Exporting results to {output_file}...")
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = [
            'oe_workers', 'api_workers', 'throughput', 'total_duration_sec',
            'min_latency', 'avg_latency', 'max_latency', 'success_rate',
            'sc_min', 'sc_avg', 'sc_max',
            'mq_min', 'mq_avg', 'mq_max',
            'oe_min', 'oe_avg', 'oe_max',
            'oe_internal_avg_ms',
            'oe_internal_max_ms',
            'deploy_min', 'deploy_avg', 'deploy_max',
            'totals_min', 'totals_avg', 'totals_max',
            'oe_cpu_avg', 'oe_cpu_max', 'oe_mem_avg_mib', 'oe_mem_max_mib',
            'rabbitmq_cpu', 'orchestrator_cpu', 'catalog_cpu', 'topology_cpu'
        ]
        fieldnames += [
            'mq_p50', 'mq_p90', 'mq_p95', 'mq_p99',
            'oe_int_p50', 'oe_int_p90', 'oe_int_p95', 'oe_int_p99'
        ]

        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in comparison_results:
            # Calculate OE CPU stats
            oe_cpus = [stats['cpu'] for name, stats in result['resource_stats'].items() 
                      if 'optimization-engine' in name]
            oe_cpu_avg = sum(oe_cpus) / len(oe_cpus) if oe_cpus else 0
            oe_cpu_max = max(oe_cpus) if oe_cpus else 0
            oe_mems = [
            stats['memory_mib']
                for name, stats in result['resource_stats'].items()
                if 'optimization-engine' in name
            ]

            oe_mem_avg = sum(oe_mems) / len(oe_mems) if oe_mems else 0
            oe_mem_max = max(oe_mems) if oe_mems else 0

            
            # Get infrastructure CPU
            def get_cpu(keyword):
                for name, stats in result['resource_stats'].items():
                    if keyword in name.lower():
                        return stats['cpu']
                return 0
            
            oe_internal = result.get('oe_internal_times', [])

            oe_internal_avg = (
                sum(oe_internal) / len(oe_internal)
                if oe_internal else 0
            )
            oe_internal_max = max(oe_internal) if oe_internal else 0
            mq_p = result.get('mq_percentiles', {})
            oe_p = result.get('oe_internal_percentiles', {})

            row = {
                'oe_workers': result['num_oe_instances'],
                'api_workers': result['num_workers'],
                'throughput': result['throughput'],
                'total_duration_sec': result['total_duration'],
                'min_latency': result['min_latency'] * 1000,  # Convert to ms
                'avg_latency': result['avg_latency'] * 1000,
                'max_latency': result['max_latency'] * 1000,
                'success_rate': (result['successful'] / result['num_requests']) * 100,
                
                # Component timings (ms)
                'sc_min': result['results_total']['sc']['min'] * 1000,
                'sc_avg': result['results_total']['sc']['avg'] * 1000,
                'sc_max': result['results_total']['sc']['max'] * 1000,
                
                'mq_min': result['results_total']['mq']['min'] * 1000,
                'mq_avg': result['results_total']['mq']['avg'] * 1000,
                'mq_max': result['results_total']['mq']['max'] * 1000,
                
                'oe_min': result['results_total']['OE']['min'] * 1000,
                'oe_avg': result['results_total']['OE']['avg'] * 1000,
                'oe_max': result['results_total']['OE']['max'] * 1000,
                
                'deploy_min': result['results_total']['deploy']['min'] * 1000,
                'deploy_avg': result['results_total']['deploy']['avg'] * 1000,
                'deploy_max': result['results_total']['deploy']['max'] * 1000,
                
                'totals_min': result['results_total']['totals']['min'] * 1000,
                'totals_avg': result['results_total']['totals']['avg'] * 1000,
                'totals_max': result['results_total']['totals']['max'] * 1000,
                
                # CPU stats
                'oe_cpu_avg': oe_cpu_avg,
                'oe_cpu_max': oe_cpu_max,
                'oe_mem_avg_mib': oe_mem_avg,
                'oe_mem_max_mib': oe_mem_max,
                'rabbitmq_cpu': get_cpu('rabbitmq'),
                'orchestrator_cpu': get_cpu('orchestrator'),
                'catalog_cpu': get_cpu('catalog'),
                'topology_cpu': get_cpu('topology')
            }
            row.update({
                'oe_internal_avg_ms': oe_internal_avg,
                'oe_internal_max_ms': oe_internal_max,
            })
            row.update({
                'mq_p50': mq_p.get(50, 0) * 1000,   # if mq is in seconds
                'mq_p90': mq_p.get(90, 0) * 1000,
                'mq_p95': mq_p.get(95, 0) * 1000,
                'mq_p99': mq_p.get(99, 0) * 1000,

                'oe_int_p50': oe_p.get(50, 0),
                'oe_int_p90': oe_p.get(90, 0),
                'oe_int_p95': oe_p.get(95, 0),
                'oe_int_p99': oe_p.get(99, 0),
            })

       
            writer.writerow(row)
    
    print(f"✅ CSV exported successfully!")
    print(f"\nTo generate plots, run:")
    print(f"  python generate_plots.py")

def run_scaling_comparison(scaling_configs, requests_per_config=NUM_REQUESTS, num_workers=MAX_WORKERS):
    """Run benchmarks with different OE scaling configurations"""
    print("\n" + "="*60)
    print("🚀 SCALING COMPARISON BENCHMARK")
    print("="*60)

    comparison_results = []

    for num_instances in scaling_configs:
        if not scale_optimization_engine(num_instances):
            print(f"Failed to scale to {num_instances} instances, skipping...")
            continue
            
        #for num_worker in [num_workers]: #[2**i for i in range(100) if 2**i <= num_workers]:
        for num_worker in [2**i for i in range(100) if 2**i <= num_workers]:
            print(f"\n{'#'*60}")
            print(f"# Testing: {num_instances} OE workers, {num_worker} API workers")
            print(f"{'#'*60}")

            result = run_benchmark(num_requests=requests_per_config, num_workers=num_worker)
            result['num_oe_instances'] = num_instances
            result['num_workers'] = num_worker
            comparison_results.append(result)

            time.sleep(2)

        subprocess.run(
            ["docker", "compose", "down"],
            cwd='/home/ananos/SMO/deployment/compose'
        )
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd='/home/ananos/SMO/deployment/compose'
        )

        time.sleep(2)
        subprocess.run(
            ["bash", "-x", "topology.sh"],
            cwd='/home/ananos/SMO/'
        )        
        subprocess.run(
            ["bash", "-x", "catalog.sh"],
            cwd='/home/ananos/SMO/'
        )


    # Print summary
    print("\n" + "="*60)
    print("📊 SCALING COMPARISON SUMMARY")
    print("="*60)
    print(f"{'OE':>3} {'API':>3} {'Thru':>6} {'Avg(ms)':>8} {'Max(ms)':>8} {'Success%':>8}")
    print("-"*60)

    for result in comparison_results:
        print(f"{result['num_oe_instances']:>3} {result['num_workers']:>3} "
              f"{result['throughput']:>6.1f} {result['avg_latency']*1000:>8.0f} "
              f"{result['max_latency']*1000:>8.0f} {result['successful']/result['num_requests']*100:>8.1f}")

    print("="*60)

    # Export to CSV
    export_to_csv(comparison_results)

    # Cleanup
    print("\n🧹 Cleaning up OE instances...")
    subprocess.run(
        ['docker', 'compose', 'stop', 'smo-optimization-engine'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True
    )
    subprocess.run(
        ['docker', 'compose', 'rm', '-f', 'smo-optimization-engine'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True
    )
    print("✅ Cleanup complete\n")

    return comparison_results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SMO Benchmarking Tool with CSV Export')
    parser.add_argument('--requests', type=int, default=100,
                       help='Number of requests to send (default: 100)')
    parser.add_argument('--workers', type=int, default=20,
                       help='Number of concurrent API workers (default: 20)')
    parser.add_argument('--scale-comparison', type=int, default=8,
                       help='Run scaling comparison up to N OE instances (default: 8)')
    parser.add_argument('--scale', type=int,
                       help='Scale OE to specific number before benchmark')
    parser.add_argument('--output', type=str, default='scaling_data.csv',
                       help='Output CSV file (default: scaling_data.csv)')

    args = parser.parse_args()

    try:
        if args.scale_comparison and not args.scale:
            run_scaling_comparison(
                scaling_configs=[2**i for i in range(100) if 2**i <= args.scale_comparison],
                requests_per_config=args.requests,
                num_workers=args.workers
            )
        else:
            if args.scale:
                scale_optimization_engine(args.scale)

            result = run_benchmark(num_requests=args.requests, num_workers=args.workers)
            
            # Export single result to CSV
            export_to_csv([result], output_file=args.output)

    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during benchmark: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
