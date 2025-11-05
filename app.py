import psutil
import platform
from datetime import datetime
from flask import Flask, render_template, jsonify
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_system_info():
    """Get comprehensive system information"""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        cpu_count = psutil.cpu_count()
        total_memory = round(psutil.virtual_memory().total / (1024**3), 2)
        platform_info = f"{platform.system()} {platform.release()}"
        
        return {
            'boot_time': boot_time,
            'cpu_count': cpu_count,
            'total_memory': total_memory,
            'platform_info': platform_info
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {
            'boot_time': 'N/A',
            'cpu_count': 'N/A',
            'total_memory': 'N/A',
            'platform_info': 'N/A'
        }

def get_disk_usage():
    """Get disk usage percentage"""
    try:
        disk_usage = psutil.disk_usage('/')
        return round((disk_usage.used / disk_usage.total) * 100, 1)
    except Exception as e:
        logger.error(f"Error getting disk usage: {e}")
        return 0

def get_alert_message(cpu_metric, mem_metric, disk_metric):
    """Generate appropriate alert message based on metrics"""
    critical_threshold = 80
    warning_threshold = 60
    
    critical_services = []
    warning_services = []
    
    if cpu_metric > critical_threshold:
        critical_services.append("CPU")
    elif cpu_metric > warning_threshold:
        warning_services.append("CPU")
        
    if mem_metric > critical_threshold:
        critical_services.append("Memory")
    elif mem_metric > warning_threshold:
        warning_services.append("Memory")
        
    if disk_metric > critical_threshold:
        critical_services.append("Disk")
    elif disk_metric > warning_threshold:
        warning_services.append("Disk")
    
    if critical_services:
        return f"🚨 CRITICAL: High {', '.join(critical_services)} usage detected! Consider scaling up or optimizing resources."
    elif warning_services:
        return f"⚠️ WARNING: Elevated {', '.join(warning_services)} usage detected. Monitor closely."
    else:
        return "✅ All systems operating normally."

@app.route("/")
def index():
    """Main dashboard route"""
    try:
        # Get system metrics
        cpu_metric = psutil.cpu_percent(interval=1)
        mem_metric = psutil.virtual_memory().percent
        disk_metric = get_disk_usage()
        
        # Get system information
        system_info = get_system_info()
        
        # Generate alert message
        message = get_alert_message(cpu_metric, mem_metric, disk_metric)
        
        # Log metrics
        logger.info(f"Metrics - CPU: {cpu_metric}%, Memory: {mem_metric}%, Disk: {disk_metric}%")
        
        return render_template(
            "index.html",
            cpu_metric=cpu_metric,
            mem_metric=mem_metric,
            disk_metric=disk_metric,
            message=message,
            **system_info
        )
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template(
            "index.html",
            cpu_metric=0,
            mem_metric=0,
            disk_metric=0,
            message="Error retrieving system metrics",
            boot_time="N/A",
            cpu_count="N/A",
            total_memory="N/A",
            platform_info="N/A"
        )

@app.route("/api/metrics")
def api_metrics():
    """API endpoint for metrics (for future integrations)"""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": get_disk_usage(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "cpu_count": psutil.cpu_count(),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error in API metrics: {e}")
        return jsonify({"error": "Failed to retrieve metrics"}), 500

@app.route("/health")
def health_check():
    """Health check endpoint for Kubernetes"""
    try:
        # Basic health check
        cpu_metric = psutil.cpu_percent(interval=0.1)
        mem_metric = psutil.virtual_memory().percent
        
        if cpu_metric < 95 and mem_metric < 95:
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200
        else:
            return jsonify({"status": "unhealthy", "reason": "High resource usage"}), 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "reason": str(e)}), 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask application on port {port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)