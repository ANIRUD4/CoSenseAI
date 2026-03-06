import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import time
import numpy as np
from backend.storage.metrics_store import load_metrics

def generate_accuracy_graph():
    """Generates a Base64-encoded PNG graph of accuracy over time."""
    data = load_metrics()
    events = data.get("events", [])
    
    if not events:
        return None

    # Calculate rolling accuracy
    window = 20
    timestamps = []
    accuracies = []
    
    current_correct = 0
    for i, event in enumerate(events):
        if event["confirmed"]:
            current_correct += 1
        
        # Simple cumulative accuracy for plotting
        accuracies.append(current_correct / (i + 1))
        # Format timestamp to be readable (e.g., MM-DD HH:MM)
        timestamps.append(time.strftime('%m-%d %H:%M', time.localtime(event["timestamp"])))

    # Only plot every N-th point if there are too many
    if len(accuracies) > 100:
        step = len(accuracies) // 50
        accuracies = accuracies[::step]
        timestamps = timestamps[::step]

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, accuracies, marker='o', linestyle='-', color='#1e88e5', linewidth=2)
    plt.title('System Accuracy Trend (Real-world Feedback)', fontsize=14, fontweight='bold')
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Cumulative Accuracy', fontsize=12)
    plt.ylim(0, 1.1)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    buf.seek(0)
    
    return base64.b64encode(buf.read()).decode('utf-8')

def generate_class_performance_graph():
    """Generates a bar chart of accuracy per class if snapshots exist."""
    data = load_metrics()
    snapshots = data.get("snapshots", [])
    
    if not snapshots:
        return None
        
    latest = snapshots[-1]
    metrics = latest.get("class_metrics", {})
    
    labels = list(metrics.keys())
    f1_scores = [m.get("f1", 0) for m in metrics.values()]
    
    plt.figure(figsize=(10, 5))
    colors = plt.cm.viridis(np.linspace(0, 1, len(labels)))
    plt.bar(labels, f1_scores, color=colors)
    plt.title('Performance by Class (Latest Benchmark)', fontsize=14, fontweight='bold')
    plt.xlabel('Class', fontsize=12)
    plt.ylabel('F1-Score', fontsize=12)
    plt.ylim(0, 1.1)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    buf.seek(0)
    
    return base64.b64encode(buf.read()).decode('utf-8')
