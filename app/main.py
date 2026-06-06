"""
BookVault API - A simple book inventory management system.
This is the application you'll be deploying and managing as a DevOps engineer.
DO NOT modify this code — your job is to deploy, secure, and monitor it.
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bookvault")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "bookvault"),
    "user": os.getenv("DB_USER", "bookvault"),
    "password": os.getenv("DB_PASSWORD", "changeme"),
}

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "bookvault_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "bookvault_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id          SERIAL PRIMARY KEY,
                    title       VARCHAR(255) NOT NULL,
                    author      VARCHAR(255) NOT NULL,
                    isbn        VARCHAR(13) UNIQUE,
                    genre       VARCHAR(100),
                    year        INTEGER,
                    stock       INTEGER DEFAULT 0,
                    created_at  TIMESTAMP DEFAULT NOW(),
                    updated_at  TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id          SERIAL PRIMARY KEY,
                    action      VARCHAR(50) NOT NULL,
                    book_id     INTEGER,
                    details     TEXT,
                    created_at  TIMESTAMP DEFAULT NOW()
                );
            """)
            # Seed data
            cur.execute("SELECT count(*) AS cnt FROM books;")
            if cur.fetchone()["cnt"] == 0:
                seed = [
                    ("Cien años de soledad", "Gabriel García Márquez", "9780060883287", "Fiction", 1967, 12),
                    ("Don Quijote de la Mancha", "Miguel de Cervantes", "9780060934347", "Classic", 1605, 8),
                    ("El Principito", "Antoine de Saint-Exupéry", "9780156012195", "Fiction", 1943, 20),
                    ("1984", "George Orwell", "9780451524935", "Dystopia", 1949, 15),
                    ("Clean Code", "Robert C. Martin", "9780132350884", "Tech", 2008, 5),
                ]
                for title, author, isbn, genre, year, stock in seed:
                    cur.execute(
                        "INSERT INTO books (title,author,isbn,genre,year,stock) VALUES (%s,%s,%s,%s,%s,%s)",
                        (title, author, isbn, genre, year, stock),
                    )
                logger.info("Seeded %d books", len(seed))
        conn.commit()
    logger.info("Database initialized")


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

@app.before_request
def start_timer():
    request._start_time = time.time()


@app.after_request
def record_metrics(response):
    latency = time.time() - getattr(request, "_start_time", time.time())
    endpoint = request.path
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, endpoint).observe(latency)
    return response


# ---------------------------------------------------------------------------
# Health & Metrics
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    """Liveness probe."""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.route("/ready")
def readiness():
    """Readiness probe — checks DB connectivity."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return jsonify({"status": "ready"})
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return jsonify({"status": "not_ready", "error": str(exc)}), 503


@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# ---------------------------------------------------------------------------
# CRUD — Books
# ---------------------------------------------------------------------------

@app.route("/api/v1/books", methods=["GET"])
def list_books():
    genre = request.args.get("genre")
    search = request.args.get("q")
    with get_db() as conn:
        with conn.cursor() as cur:
            query = "SELECT * FROM books WHERE 1=1"
            params = []
            if genre:
                query += " AND genre = %s"
                params.append(genre)
            if search:
                query += " AND (title ILIKE %s OR author ILIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
            query += " ORDER BY id;"
            cur.execute(query, params)
            books = cur.fetchall()
    return jsonify(books)


@app.route("/api/v1/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM books WHERE id = %s;", (book_id,))
            book = cur.fetchone()
    if not book:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book)


@app.route("/api/v1/books", methods=["POST"])
def create_book():
    data = request.get_json(force=True)
    required = ["title", "author"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO books (title,author,isbn,genre,year,stock)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING *;""",
                (data["title"], data["author"], data.get("isbn"),
                 data.get("genre"), data.get("year"), data.get("stock", 0)),
            )
            book = cur.fetchone()
            cur.execute(
                "INSERT INTO audit_log (action,book_id,details) VALUES (%s,%s,%s);",
                ("CREATE", book["id"], f"Created: {data['title']}"),
            )
        conn.commit()
    logger.info("Book created: %s", book["id"])
    return jsonify(book), 201


@app.route("/api/v1/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(force=True)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM books WHERE id = %s;", (book_id,))
            if not cur.fetchone():
                return jsonify({"error": "Book not found"}), 404
            cur.execute(
                """UPDATE books SET title=%s, author=%s, isbn=%s, genre=%s,
                   year=%s, stock=%s, updated_at=NOW() WHERE id=%s RETURNING *;""",
                (data.get("title"), data.get("author"), data.get("isbn"),
                 data.get("genre"), data.get("year"), data.get("stock"), book_id),
            )
            book = cur.fetchone()
            cur.execute(
                "INSERT INTO audit_log (action,book_id,details) VALUES (%s,%s,%s);",
                ("UPDATE", book_id, f"Updated fields: {list(data.keys())}"),
            )
        conn.commit()
    return jsonify(book)


@app.route("/api/v1/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM books WHERE id=%s RETURNING id;", (book_id,))
            deleted = cur.fetchone()
            if not deleted:
                return jsonify({"error": "Book not found"}), 404
            cur.execute(
                "INSERT INTO audit_log (action,book_id,details) VALUES (%s,%s,%s);",
                ("DELETE", book_id, f"Deleted book {book_id}"),
            )
        conn.commit()
    return jsonify({"message": "Book deleted"}), 200


@app.route("/api/v1/audit", methods=["GET"])
def audit_log():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 50;")
            logs = cur.fetchall()
    return jsonify(logs)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("APP_PORT", 5000))
    app.run(host="0.0.0.0", port=port)
