"""
LLM Audit Logging
==================

Helper functions to log all LLM operations for debugging and optimization.
Tracks raw responses, token usage, latency, and costs.
"""
import json
import time
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
from ..config import DB_PATH, LLM_MODEL, get_db_connection


def _iso_now():
    """Get current timestamp in ISO format"""
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    """Estimate cost in USD based on token usage

    Pricing (as of 2025):
    - gpt-4o-mini: $0.15/1M input, $0.60/1M output
    - gpt-4o: $2.50/1M input, $10.00/1M output
    - gpt-3.5-turbo: $0.50/1M input, $1.50/1M output
    """
    pricing = {
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
        "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
        "gpt-3.5-turbo": (0.50 / 1_000_000, 1.50 / 1_000_000),
    }

    # Find matching pricing (handle versioned models like gpt-4o-mini-2024-07-18)
    input_price, output_price = (0, 0)
    for model_prefix, prices in pricing.items():
        if model.startswith(model_prefix):
            input_price, output_price = prices
            break

    cost = (tokens_input * input_price) + (tokens_output * output_price)
    return round(cost, 6)


def log_llm_operation(
    operation_type: str,
    model: str,
    prompt_text: str,
    raw_response: str,
    parsed_output: Dict[str, Any],
    duration_ms: int,
    note_id: Optional[str] = None,
    prompt_version: Optional[str] = None,
    tokens_input: Optional[int] = None,
    tokens_output: Optional[int] = None,
    error: Optional[str] = None,
    success: bool = True,
    db_connection = None
) -> int:
    """Log an LLM operation to the audit table

    Args:
        operation_type: Type of operation ('classification', 'enrichment', 'consolidation', 'search_parse')
        model: Model name used
        prompt_text: Full prompt sent to LLM
        raw_response: Raw LLM response (usually JSON string)
        parsed_output: Parsed/validated output (dict)
        duration_ms: Operation duration in milliseconds
        note_id: Optional note ID being processed
        prompt_version: Optional prompt template version/hash
        tokens_input: Input tokens used
        tokens_output: Output tokens generated
        error: Error message if operation failed
        success: Whether operation succeeded

    Returns:
        operation_id: ID of the logged operation
    """
    # Use provided connection or create new one
    should_close = db_connection is None
    if db_connection is None:
        con = get_db_connection()
    else:
        con = db_connection

    cur = con.cursor()

    # Calculate cost if tokens provided
    cost_usd = None
    if tokens_input is not None and tokens_output is not None:
        cost_usd = _estimate_cost(model, tokens_input, tokens_output)

    # Serialize parsed output
    parsed_output_json = json.dumps(parsed_output) if parsed_output else None

    cur.execute("""
        INSERT INTO llm_operations (
            note_id, operation_type, created, model, prompt_version,
            duration_ms, tokens_input, tokens_output, cost_usd,
            prompt_text, raw_response, parsed_output,
            error, success
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        note_id, operation_type, _iso_now(), model, prompt_version,
        duration_ms, tokens_input, tokens_output, cost_usd,
        prompt_text, raw_response, parsed_output_json,
        error, success
    ))

    operation_id = cur.lastrowid

    # Only commit and close if we created the connection
    if should_close:
        con.commit()
        con.close()

    return operation_id


@contextmanager
def track_llm_call(
    operation_type: str,
    prompt_text: str,
    note_id: Optional[str] = None,
    prompt_version: Optional[str] = None,
    db_connection = None
):
    """Context manager to track LLM call timing and results

    Usage:
        with track_llm_call('classification', prompt, note_id) as tracker:
            response = await llm.ainvoke(prompt)
            tracker.set_response(response)
            result = json.loads(response.content)
            tracker.set_parsed_output(result)
        # Auto-logged on context exit

    Yields:
        Tracker object with set_response() and set_parsed_output() methods
    """
    class Tracker:
        def __init__(self):
            self.start_time = time.time()
            self.response = None
            self.parsed_output = None
            self.error = None
            self.success = True

        def set_response(self, response):
            """Store LLM response object"""
            self.response = response

        def set_parsed_output(self, parsed_output):
            """Store parsed/validated output"""
            self.parsed_output = parsed_output

        def set_error(self, error: Exception):
            """Mark operation as failed"""
            self.error = str(error)
            self.success = False

    tracker = Tracker()

    try:
        yield tracker
    except Exception as e:
        tracker.set_error(e)
        raise
    finally:
        # Calculate duration
        duration_ms = int((time.time() - tracker.start_time) * 1000)

        # Extract tokens from response (if available)
        tokens_input = None
        tokens_output = None
        raw_response = None

        if tracker.response:
            raw_response = tracker.response.content if hasattr(tracker.response, 'content') else str(tracker.response)

            # Extract token usage from response metadata (LangChain format)
            if hasattr(tracker.response, 'response_metadata'):
                metadata = tracker.response.response_metadata
                if 'token_usage' in metadata:
                    tokens_input = metadata['token_usage'].get('prompt_tokens')
                    tokens_output = metadata['token_usage'].get('completion_tokens')

        # Log the operation using provided connection (part of same transaction)
        try:
            log_llm_operation(
                operation_type=operation_type,
                model=LLM_MODEL,
                prompt_text=prompt_text,
                raw_response=raw_response or "",
                parsed_output=tracker.parsed_output or {},
                duration_ms=duration_ms,
                note_id=note_id,
                prompt_version=prompt_version,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                error=tracker.error,
                success=tracker.success,
                db_connection=db_connection  # Use shared connection!
            )
        except sqlite3.OperationalError as e:
            # Silently ignore database locks - audit logging is not critical
            print(f"Warning: Audit logging skipped due to: {e}")


def get_operation_stats(operation_type: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
    """Get statistics about LLM operations

    Args:
        operation_type: Optional filter by operation type
        days: Number of days to look back (default: 7)

    Returns:
        Dict with statistics (total_ops, avg_duration, total_cost, etc.)
    """
    # Use WAL mode for concurrent access
    con = sqlite3.connect(DB_PATH, timeout=30.0)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()

    # Build query
    where_clause = "WHERE created >= datetime('now', '-{} days')".format(days)
    if operation_type:
        where_clause += f" AND operation_type = '{operation_type}'"

    cur.execute(f"""
        SELECT
            COUNT(*) as total_operations,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
            AVG(duration_ms) as avg_duration_ms,
            MAX(duration_ms) as max_duration_ms,
            SUM(tokens_input) as total_tokens_input,
            SUM(tokens_output) as total_tokens_output,
            SUM(cost_usd) as total_cost_usd,
            AVG(cost_usd) as avg_cost_usd
        FROM llm_operations
        {where_clause}
    """)

    row = cur.fetchone()
    con.close()

    return {
        "total_operations": row[0] or 0,
        "successful": row[1] or 0,
        "failed": row[2] or 0,
        "avg_duration_ms": round(row[3], 2) if row[3] else 0,
        "max_duration_ms": row[4] or 0,
        "total_tokens_input": row[5] or 0,
        "total_tokens_output": row[6] or 0,
        "total_cost_usd": round(row[7], 6) if row[7] else 0,
        "avg_cost_usd": round(row[8], 6) if row[8] else 0
    }
