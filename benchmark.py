import time
import requests
from statistics import mean, stdev

API_URL = "http://localhost:8000"

def benchmark_query(question: str, iterations: int = 10):
    """Benchmark query performance"""
    times = []
    
    print(f"\n🔍 Benchmarking: '{question}'")
    print(f"Iterations: {iterations}")
    
    for i in range(iterations):
        start = time.time()
        try:
            response = requests.post(
                f"{API_URL}/query",
                json={"question": question}
            )
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"  [{i+1}/{iterations}] {elapsed:.3f}s - {response.status_code}")
        except Exception as e:
            print(f"  [{i+1}/{iterations}] ERROR: {e}")
    
    if times:
        print(f"\n📊 Results:")
        print(f"  Mean: {mean(times):.3f}s")
        print(f"  Min: {min(times):.3f}s")
        print(f"  Max: {max(times):.3f}s")
        if len(times) > 1:
            print(f"  StdDev: {stdev(times):.3f}s")

if __name__ == "__main__":
    queries = [
        "Who scored the highest in Math?",
        "Show all students with grade A",
        "What is the average score?"
    ]
    
    for query in queries:
        benchmark_query(query, iterations=5)
