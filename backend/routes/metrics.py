from fastapi import APIRouter, BackgroundTasks
from backend.storage.metrics_store import load_metrics, get_rolling_accuracy, log_snapshot
from backend.utils.visualization import generate_accuracy_graph, generate_class_performance_graph
from scripts.evaluate_accuracy import evaluate_accuracy
import time

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/summary")
def get_metrics_summary():
    """Returns a high-level summary of system performance."""
    data = load_metrics()
    
    total = data["total_confirmed"] + data["total_corrected"]
    global_accuracy = data["total_confirmed"] / total if total > 0 else 0.0
    rolling_50 = get_rolling_accuracy(50)
    
    return {
        "global_accuracy": round(global_accuracy, 4),
        "rolling_50_accuracy": round(rolling_50, 4),
        "total_feedbacks": total,
        "total_confirmed": data["total_confirmed"],
        "total_corrected": data["total_corrected"],
        "last_updated": time.time()
    }

@router.get("/graph/accuracy")
def get_accuracy_graph():
    """Returns a Base64-encoded PNG of the accuracy trend."""
    graph_data = generate_accuracy_graph()
    return {"format": "png", "encoding": "base64", "data": graph_data}

@router.get("/graph/class-performance")
def get_class_performance_graph():
    """Returns a Base64-encoded PNG of per-class performance."""
    graph_data = generate_class_performance_graph()
    return {"format": "png", "encoding": "base64", "data": graph_data}

@router.post("/benchmark")
def run_benchmark(background_tasks: BackgroundTasks, dataset_path: str = "dataset"):
    """
    Triggers a full accuracy evaluation in the background 
    and saves a snapshot of the results.
    """
    def task():
        accuracy, class_metrics = evaluate_accuracy(dataset_path)
        log_snapshot(accuracy, class_metrics)
        
    background_tasks.add_task(task)
    return {"message": "Benchmark started in background."}

