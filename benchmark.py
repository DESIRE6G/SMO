#!/usr/bin/env python3
"""
SMO Benchmarking Script
Measures latency, throughput, and resource usage for different scaling configurations
"""

import requests
import time
import json
import subprocess
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys

# Configuration
SERVICE_ORCHESTRATOR_URL = "http://localhost:8000/services"
SERVICE_NAME = "demo1_nsd.sg.yml"
NUM_REQUESTS = 100  # Number of requests to send
MAX_WORKERS = 8     # Concurrent request threads
MIN_WORKERS = 1     # Concurrent request threads

import os
import psutil  # run: pip install psutil

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
    Supports:
      - systemd (docker-<id>.scope)
      - legacy /sys/fs/cgroup/docker/<id>
      - rootless Docker
      - Podman
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

    # As last resort: search system.slice for matching scope name
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


def send_deployment_request():
    """Send a single deployment request and measure latency"""
    start_time = time.time()
    try:
        response = requests.post(
            SERVICE_ORCHESTRATOR_URL,
            json={"name": SERVICE_NAME},
            timeout=120  # 2 minute timeout
        )
        end_time = time.time()
        latency = end_time - start_time
        #print(latency)
        #import pdb;pdb.set_trace()
        #print(response.json()['measurements'])
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
    Computes CPU usage as % of host total CPU capacity.
    """
    container_paths = {}        # container_name -> cgroup path
    prev_cpu_usage = {}         # container_name -> prev usage_usec
    prev_time = time.time()
    num_cpus = psutil.cpu_count(logical=True)

    try:
        while not stop_event.is_set():
            # Discover SMO containers dynamically
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            container_names = [
                name.strip()
                for name in result.stdout.splitlines()
                if 'smo-' in name  # only SMO containers
            ]

            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt <= 0:
                dt = 0.1

            for cname in container_names:

                # Resolve container ID and cgroup path if not cached
                if cname not in container_paths:
                    cid = get_container_id(cname)
                    try:
                        container_paths[cname] = get_cgroup_path(cid)
                    except FileNotFoundError:
                        continue  # skip containers that exited immediately

                cgpath = container_paths[cname]

                # ------- CPU USAGE -------
                cpu_now = read_cpu_usage_usec(cgpath)
                cpu_prev = prev_cpu_usage.get(cname, cpu_now)

                # Convert from microseconds to CPU cores used
                cpu_used_cores = (cpu_now - cpu_prev) / 1_000_000.0 / dt
                prev_cpu_usage[cname] = cpu_now

                # Convert to percent of host CPU
                cpu_percent = (cpu_used_cores / num_cpus) * 100
                if cpu_percent < 0:
                    cpu_percent = 0

                # ------- MEMORY USAGE -------
                mem_bytes = read_memory_current(cgpath)
                mem_str = f"{mem_bytes / (1024*1024):.1f}MiB"

                #print(f"cpu: {cpu_percent}, mem: {mem_str}")
                # ------- TRACK PEAKS -------
                if cname not in max_stats_dict:
                    max_stats_dict[cname] = {
                        'cpu': cpu_percent,
                        'memory': mem_str
                    }
                else:
                    if cpu_percent > max_stats_dict[cname]['cpu']:
                        max_stats_dict[cname]['cpu'] = cpu_percent
                        max_stats_dict[cname]['memory'] = mem_str

            #time.sleep(0.2)
            #print(max_stats_dict)

    except Exception as e:
        print(f"Warning: Error monitoring cgroup stats: {e}")

def get_container_stats():
    """Get CPU and memory stats for all SMO containers (single snapshot)"""
    try:
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format',
             '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'],
            capture_output=True,
            text=True,
            timeout=10
        )

        lines = result.stdout.strip().split('\n')
        stats = {}

        for line in lines:
            if not line.strip():
                continue

            parts = line.split('\t')
            if len(parts) >= 3:
                container_name = parts[0].strip()
                # Only include SMO containers and compose containers
                if 'smo-' in container_name or 'compose-smo-' in container_name or 'optimization-engine' in container_name:
                    cpu_percent = parts[1].strip()
                    mem_usage = parts[2].strip()

                    stats[container_name] = {
                        'cpu': cpu_percent,
                        'memory': mem_usage
                    }

        return stats
    except Exception as e:
        print(f"Warning: Could not get container stats: {e}")
        return {}


def scale_optimization_engine(num_instances):
    """Scale the optimization engine to specified number of instances"""
    print(f"\n🔧 Scaling Optimization Engine to {num_instances} instances...")

    # Stop ALL existing OE instances first
    subprocess.run(
        ['docker', 'compose', 'stop', 'smo-optimization-engine'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True
    )

    # Remove ALL existing OE instances
    subprocess.run(
        ['docker', 'compose', 'rm', '-f', 'smo-optimization-engine'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True
    )

    # Start with scaling
    result = subprocess.run(
        ['docker', 'compose', 'up', '-d', '--scale', f'smo-optimization-engine={num_instances}'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error scaling: {result.stderr}")
        return False

    # Wait for containers to be ready
    print("⏳ Waiting for containers to initialize...")
    time.sleep(10)  # Increased from 5 to 10 seconds

    # Verify instances are running
    ps_result = subprocess.run(
        ['docker', 'compose', 'ps'],
        cwd='/home/ananos/SMO/deployment/compose',
        capture_output=True,
        text=True
    )

    # Debug: print raw output if count is 0
    # Count lines containing both "optimization-engine" and "Up"
    running_count = sum(1 for line in ps_result.stdout.split('\n')
                       if 'optimization-engine' in line and 'Up' in line)

    if running_count == 0:
        print(f"⚠️  Warning: 0 instances detected. Debug info:")
        print(f"   Return code: {ps_result.returncode}")
        print(f"   Stderr: {ps_result.stderr}")
        # Check with docker ps directly
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

    # Start monitoring thread with shared dictionary
    stop_monitoring = threading.Event()
    max_stats = {}
    monitor_thread = threading.Thread(
        target=monitor_container_stats,
        args=(stop_monitoring, max_stats),
        daemon=True
    )

    # Record overall start time
    overall_start = time.time()
    monitor_thread.start()

    # Send requests concurrently
    results = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(send_deployment_request) for _ in range(num_requests)]

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)

            # Progress indicator
            if i % 100 == 0:
                print(f"  Progress: {i}/{num_requests} requests completed")

    overall_end = time.time()
    overall_duration = overall_end - overall_start

    # Stop monitoring and get stats
    stop_monitoring.set()
    monitor_thread.join(timeout=5)
    #print(max_stats)

    # Format CPU values with % sign
    final_stats = {}
    for container_name, stats in max_stats.items():
        final_stats[container_name] = {
            'cpu': f"{stats['cpu']:.2f}%",
            'memory': stats['memory']
        }

    # Calculate metrics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    latencies = [r['latency'] for r in results]
    timings = [r['timings'] for r in results]
    #print(timings)
    #from_response = sum(timings[0][k] for k in ['sc','mq','OE']) + sum(d['site_retrieve'] + d['deploy'] for d in data[0]['deploy'])
    # Initialize lists for each field
    sc_list, mq_list, oe_list, deploy_list, totals = [], [], [], [], []

    for entry in timings:
        sc_list.append(entry['sc'])
        mq_list.append(entry['mq'])
        oe_list.append(entry['OE'])
        # Aggregate deploy per entry
        deploy_total = sum(d['site_retrieve'] + d['deploy'] for d in entry['deploy'])
        deploy_list.append(deploy_total)
        total = entry['sc'] + entry['mq'] + entry['OE'] + deploy_total
        totals.append(total)

    def stats(lst):
        return {
            'avg': sum(lst)/len(lst),
            'min': min(lst),
            'max': max(lst)
        }

    results_total = {
        'sc': stats(sc_list),
        'mq': stats(mq_list),
        'OE': stats(oe_list),
        'deploy': stats(deploy_list),
        'totals': stats(totals)
    }

    #from pprint import pprint
    #pprint(results_total)


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

    # Resource usage
    print(f"\n💻 RESOURCE USAGE (Peak values during test)")
    #print(final_stats)
    for container_name in sorted(final_stats.keys()):
        #if 'optimization-engine' in container_name or 'orchestrator' in container_name:
        stats = final_stats[container_name]
        print(f"{container_name:40s} Peak CPU: {stats['cpu']:>8s}  MEM: {stats['memory']}")

    print(f"{'='*60}\n")

    return {
        'num_requests': num_requests,
        'successful': len(successful),
        'failed': len(failed),
        'total_duration': overall_duration,
        'throughput': num_requests/overall_duration,
        'avg_latency': statistics.mean(latencies),
        'median_latency': statistics.median(latencies),
        'min_latency': min(latencies),
        'max_latency': max(latencies),
        'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
        'resource_stats': final_stats,
        'results_total': results_total
    }


def run_scaling_comparison(scaling_configs, requests_per_config=NUM_REQUESTS,num_workers=MAX_WORKERS):
    """Run benchmarks with different OE scaling configurations"""
    print("\n" + "="*60)
    print("🚀 SCALING COMPARISON BENCHMARK")
    print("="*60)

    comparison_results = []

    #num_instances = 1
    for num_instances in scaling_configs:
        ## Scale OE
        if not scale_optimization_engine(num_instances):
            print(f"Failed to scale to {num_instances} instances, skipping...")
            continue
        for num_worker in list(num_workers): #list(2**i for i in range(100) if 2**i <= num_workers):
            print(f"\n{'#'*60}")
            print(f"# Testing with {num_instances} Optimization Engine instance(s)")
            print(f"{'#'*60}")

    
            # Run benchmark
            result = run_benchmark(num_requests=requests_per_config, num_workers=num_worker)
            result['num_oe_instances'] = num_instances
            result['num_workers'] = num_worker
            comparison_results.append(result)

            # Brief pause between tests
            time.sleep(2)

        # Print comparison summary
        print("\n" + "="*60)
        print("📊 SCALING COMPARISON SUMMARY")
        print("="*60)
        print(f"{'OE Instances':>5} (#) {'Workers':>5} (#) {'Throughput':>10} (rps) {'Min Latency':>10} (ms) {'Avg Latency':>10} (ms) {'Max Latency':>10} (ms) {'Success Rate':>10} (%)")
        print("-"*60)

        for result in comparison_results:
            throughput = f"{result['throughput']:.2f}"
            oe_min = f"{result['results_total']['OE']['min']*1000:.2f}"
            sc_min = f"{result['results_total']['sc']['min']*1000:.2f}"
            mq_min = f"{result['results_total']['mq']['min']*1000:.2f}"
            deploy_min = f"{result['results_total']['deploy']['min']*1000:.2f}"
            totals_min = f"{result['results_total']['totals']['min']*1000:.2f}"
            oe_avg = f"{result['results_total']['OE']['avg']*1000:.2f}"
            sc_avg = f"{result['results_total']['sc']['avg']*1000:.2f}"
            mq_avg = f"{result['results_total']['mq']['avg']*1000:.2f}"
            deploy_avg = f"{result['results_total']['deploy']['avg']*1000:.2f}"
            totals_avg = f"{result['results_total']['totals']['avg']*1000:.2f}"
            oe_max = f"{result['results_total']['OE']['max']*1000:.2f}"
            sc_max = f"{result['results_total']['sc']['max']*1000:.2f}"
            mq_max = f"{result['results_total']['mq']['max']*1000:.2f}"
            deploy_max = f"{result['results_total']['deploy']['max']*1000:.2f}"
            totals_max = f"{result['results_total']['totals']['max']*1000:.2f}"
            avg_latency = f"{result['avg_latency']*1000:.2f}"
            min_latency = f"{result['min_latency']*1000:.2f}"
            max_latency = f"{result['max_latency']*1000:.2f}"
            success_rate = f"{result['successful']/result['num_requests']*100:.1f}"

            print(f"{result['num_oe_instances']} {result['num_workers']} {throughput} {oe_min} {sc_min} {mq_min} {deploy_min} {totals_min} {oe_avg} {sc_avg} {mq_avg} {deploy_avg} {totals_avg} {oe_max} {sc_max} {mq_max} {deploy_max} {totals_max} {min_latency} {avg_latency} {max_latency} {success_rate}")

        print("="*60)

    # Cleanup: Stop and remove all OE instances after comparison
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

    parser = argparse.ArgumentParser(description='SMO Benchmarking Tool')
    parser.add_argument('--requests', type=int, default=100,
                       help='Number of requests to send (default: 100)')
    parser.add_argument('--workers', type=int, default=20,
                       help='Number of concurrent workers (default: 20)')
    parser.add_argument('--scale-comparison', type=int, default=8,
                       help='Run scaling comparison (1, 2, 4, 8 OE instances)')
    parser.add_argument('--scale', type=int,
                       help='Scale OE to specific number of instances before benchmark')

    args = parser.parse_args()

    try:
        if args.scale_comparison and not args.scale:
            # Run comparison with different scaling configs
            run_scaling_comparison(
                scaling_configs=list(2**i for i in range(100) if 2**i <= args.scale_comparison),
                requests_per_config=args.requests,
                num_workers=args.workers
            )
        else:
            # Single benchmark run
            if args.scale:
                scale_optimization_engine(args.scale)

            run_benchmark(num_requests=args.requests, num_workers=args.workers)

    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during benchmark: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
