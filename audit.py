import threading
import queue
import time
from extensions import db
from models import AuditLog
from datetime import datetime, timedelta
from contextlib import contextmanager
import time as _time

# Flask app instance, to be set by init_app
_flask_app = None

# --- Async Audit Batching ---
class AuditBatcher:
    def __init__(self, app, batch_size=50, flush_interval=30):
        self.app = app
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.last_flush_time = None
        self.last_batch_size = 0
        self.last_flush_duration = 0
        self.total_events_logged = 0
        self.thread.start()

    def log(self, event_dict):
        try:
            self.queue.put_nowait(event_dict)
        except Exception as e:
            print(f"[AuditBatcher] Failed to queue event: {e}")

    def _run(self):
        while self.running:
            batch = []
            try:
                event = self.queue.get(timeout=self.flush_interval)
                batch.append(event)
                while len(batch) < self.batch_size:
                    try:
                        event = self.queue.get_nowait()
                        batch.append(event)
                    except queue.Empty:
                        break
            except queue.Empty:
                pass
            if batch:
                self._flush(batch)

    def _flush(self, batch):
        with self.app.app_context():
            start = _time.time()
            compressed_batch = compress_audit_events(batch)
            with db.session.no_autoflush:
                try:
                    for event_dict in compressed_batch:
                        log = AuditLog(**event_dict)
                        db.session.add(log)
                    db.session.commit()
                    duration = _time.time() - start
                    self.last_flush_time = datetime.utcnow()
                    self.last_batch_size = len(batch)
                    self.last_flush_duration = duration
                    self.total_events_logged += len(compressed_batch)
                    print(f"[AuditBatcher] Flushed {len(compressed_batch)} audit events (compressed from {len(batch)}). Duration: {duration:.3f}s. Queue size: {self.queue.qsize()}")
                except Exception as e:
                    db.session.rollback()
                    print(f"[AuditBatcher] Failed to flush batch: {e}")

    def stop(self):
        self.running = False
        self.thread.join()

    def get_stats(self):
        return {
            'last_flush_time': self.last_flush_time,
            'last_batch_size': self.last_batch_size,
            'last_flush_duration': self.last_flush_duration,
            'queue_size': self.queue.qsize(),
            'total_events_logged': self.total_events_logged,
        }

# Singleton batcher instance, initialized by init_audit
_audit_batcher = None

def compress_audit_events(events, window_seconds=60):
    """
    Compress repeated audit events within a time window into a single event.
    Increments occurrence_count and updates last_occurrence.
    """
    if not events:
        return []
    compressed = []
    events = sorted(events, key=lambda e: (
        e.get('user_id'), e.get('action'), e.get('resource_type'), e.get('resource_id'), e.get('details'), e.get('timestamp')
    ))
    prev = None
    for event in events:
        if (
            prev and
            event.get('user_id') == prev.get('user_id') and
            event.get('action') == prev.get('action') and
            event.get('resource_type') == prev.get('resource_type') and
            event.get('resource_id') == prev.get('resource_id') and
            event.get('details') == prev.get('details') and
            (event.get('timestamp') - prev.get('timestamp')).total_seconds() <= window_seconds
        ):
            prev['occurrence_count'] += 1
            prev['last_occurrence'] = event.get('timestamp')
        else:
            compressed.append(event)
            prev = event
    return compressed

def log_audit_event(
    user_id=None,
    rescue_id=None,
    action=None,
    resource_type=None,
    resource_id=None,
    details=None,
    success=True,
    error_message=None,
    execution_time=None,
    ip_address=None,
    user_agent=None,
    occurrence_count=1,
    last_occurrence=None,
):
    """
    Log an audit event to the AuditLog table (async, batched).
    Falls back to synchronous logging if batcher fails.
    """
    event_dict = dict(
        timestamp=datetime.utcnow(),
        user_id=user_id,
        rescue_id=rescue_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        success=success,
        error_message=error_message,
        execution_time=execution_time,
        ip_address=ip_address,
        user_agent=user_agent,
        occurrence_count=occurrence_count,
        last_occurrence=last_occurrence,
    )
    if not _audit_batcher:
        print("[AuditLog] AuditBatcher not initialized. Event not logged through batcher.")
        # Fallback to synchronous logging if batcher isn't ready
        if _flask_app:
            with _flask_app.app_context():
                try:
                    log = AuditLog(**event_dict)
                    db.session.add(log)
                    db.session.commit()
                    print("[AuditLog] Event logged synchronously with app context.")
                except Exception as e_sync_ctx:
                    print(f"[AuditLog] Failed to log event synchronously with app context: {e_sync_ctx}")
            return # Exit after attempting sync log with context
        else: # No flask_app, attempt without context (might fail if outside request)
            try:
                log = AuditLog(**event_dict)
                db.session.add(log)
                db.session.commit()
                print("[AuditLog] Event logged synchronously (no app context available for fallback).")
            except Exception as e_sync_no_ctx:
                print(f"[AuditLog] Failed to log event synchronously (no app context): {e_sync_no_ctx}")
        return # Exit after attempting sync log

    try:
        _audit_batcher.log(event_dict)
    except Exception as e:
        print(f"[AuditLog] Batcher failed, falling back to sync: {e}")
        try:
            log = AuditLog(**event_dict)
            db.session.add(log)
            db.session.commit()
        except Exception as e2:
            print(f"[AuditLog] Failed to log event: {e2}")

# --- Audit Aging & Cleanup ---
AUDIT_LOG_RETENTION_DAYS = 90

def cleanup_old_audit_logs(retention_days=AUDIT_LOG_RETENTION_DAYS):
    """
    Delete audit logs older than the retention period.
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    try:
        num_deleted = AuditLog.query.filter(AuditLog.timestamp < cutoff).delete(synchronize_session=False)
        db.session.commit()
        print(f"[AuditCleanup] Deleted {num_deleted} audit logs older than {retention_days} days.")
    except Exception as e:
        db.session.rollback()
        print(f"[AuditCleanup] Failed to cleanup old audit logs: {e}")

# Optional: Periodic cleanup in a background thread
class AuditCleanupThread(threading.Thread):
    def __init__(self, app, interval_hours=24, retention_days=AUDIT_LOG_RETENTION_DAYS):
        self.app = app
        super().__init__(daemon=True)
        self.interval = interval_hours * 3600
        self.retention_days = retention_days
        self.running = True

    def run(self):
        while self.running:
            with self.app.app_context():
                cleanup_old_audit_logs(self.retention_days)
            time.sleep(self.interval)

    def stop(self):
        self.running = False

_audit_cleanup_thread = None # Initialize as None

def init_audit(app_instance, start_cleanup_thread=True, cleanup_interval_hours=24, audit_retention_days=AUDIT_LOG_RETENTION_DAYS, batcher_batch_size=50, batcher_flush_interval=30):
    global _flask_app, _audit_batcher, _audit_cleanup_thread
    _flask_app = app_instance
    _audit_batcher = AuditBatcher(app=_flask_app, batch_size=batcher_batch_size, flush_interval=batcher_flush_interval)

    if start_cleanup_thread:
        _audit_cleanup_thread = AuditCleanupThread(app=_flask_app, interval_hours=cleanup_interval_hours, retention_days=audit_retention_days)
        _audit_cleanup_thread.start()

class AuditContext:
    """
    Context manager for bulk or grouped audit logging.
    Usage:
        with AuditContext(user_id=..., action='bulk_delete', resource_type='Dog', details={...}) as ctx:
            ctx.log_sub_event(action='delete', resource_id=dog_id, ...)
    At exit, logs a parent event with summary and all sub-events as children.
    """
    def __init__(self, user_id=None, rescue_id=None, action=None, resource_type=None, resource_id=None, details=None, **kwargs):
        self.parent_event = dict(
            user_id=user_id,
            rescue_id=rescue_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            **kwargs
        )
        self.sub_events = []

    def log_sub_event(self, **event):
        self.sub_events.append(event)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Log all sub-events
        for event in self.sub_events:
            log_audit_event(**event)
        # Log parent event with summary of sub-events
        self.parent_event['details']['sub_event_count'] = len(self.sub_events)
        self.parent_event['details']['sub_events'] = [
            {
                'action': e.get('action'),
                'resource_id': e.get('resource_id'),
                'success': e.get('success', True),
                'error_message': e.get('error_message'),
            } for e in self.sub_events
        ]
        log_audit_event(**self.parent_event)

def get_audit_system_stats():
    if _audit_batcher:
        return _audit_batcher.get_stats()
    return {
        'last_flush_time': None,
        'last_batch_size': 0,
        'last_flush_duration': 0,
        'queue_size': 0,
        'total_events_logged': 0,
    }