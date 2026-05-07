"""
IngatlanMonitor Dashboard
=========================
Flask alkalmazás az ingatlanok táblázatos megjelenítésére.
"""

import sqlite3
from flask import Flask, render_template, jsonify, request
from config import DATABASE, REGIONS, AIRPORT_NAMES

app = Flask(__name__)


def get_db():
    """SQLite kapcsolat létrehozása."""
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    """Dashboard főoldal."""
    return render_template("index.html", regions=REGIONS, airports=AIRPORT_NAMES)


@app.route("/api/properties")
def api_properties():
    """
    DataTables server-side processing végpont.
    Támogatott paraméterek: draw, start, length, search[value], order, columns
    Egyedi szűrők: region, min_price, max_price, min_size, min_score, show_archived, favorites_only
    """
    conn = get_db()
    cursor = conn.cursor()

    # DataTables paraméterek
    draw = request.args.get("draw", 1, type=int)
    start = request.args.get("start", 0, type=int)
    length = request.args.get("length", 25, type=int)
    search_value = request.args.get("search[value]", "")

    # Egyedi szűrők
    region = request.args.get("region", "")
    min_price = request.args.get("min_price", 0, type=int)
    max_price = request.args.get("max_price", 0, type=int)
    min_size = request.args.get("min_size", 0, type=int)
    min_score = request.args.get("min_score", 0, type=int)
    show_archived = request.args.get("show_archived", "0") == "1"
    favorites_only = request.args.get("favorites_only", "0") == "1"

    # Rendezés
    order_column_idx = request.args.get("order[0][column]", 0, type=int)
    order_dir = request.args.get("order[0][dir]", "desc")

    # Oszlop mapping (DataTables index → SQL oszlop)
    columns = [
        "score", "city", "price_eur", "size_m2", "sea_km",
        "airport", "airport_km", "parking", "garden", "garden_m2",
        "legal_status", "reason", "user_notes", "property_url", "email_date", "id"
    ]
    order_column = columns[order_column_idx] if order_column_idx < len(columns) else "score"

    # Alap WHERE feltétel
    where_clauses = []
    params = []

    if not show_archived:
        where_clauses.append("is_archived = 0")

    if favorites_only:
        where_clauses.append("is_favorite = 1")

    if region:
        where_clauses.append("region = ?")
        params.append(region)

    if min_price > 0:
        where_clauses.append("price_eur >= ?")
        params.append(min_price)

    if max_price > 0:
        where_clauses.append("price_eur <= ?")
        params.append(max_price)

    if min_size > 0:
        where_clauses.append("size_m2 >= ?")
        params.append(min_size)

    if min_score > 0:
        where_clauses.append("score >= ?")
        params.append(min_score)

    if search_value:
        where_clauses.append("(city LIKE ? OR reason LIKE ? OR user_notes LIKE ?)")
        search_pattern = f"%{search_value}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Összes rekord (szűrés nélkül)
    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_archived = 0")
    total_records = cursor.fetchone()[0]

    # Szűrt rekordok száma
    cursor.execute(f"SELECT COUNT(*) FROM properties WHERE {where_sql}", params)
    filtered_records = cursor.fetchone()[0]

    # Rendezés validálás
    if order_dir not in ("asc", "desc"):
        order_dir = "desc"

    # Adatok lekérdezése
    query = f"""
        SELECT id, email_id, email_date, portal, city, region, airport, airport_km,
               sea_km, latitude, longitude, price_eur, size_m2, parking, garden,
               score, legal_status, reason, property_url, gmail_url, maps_url,
               is_archived, is_favorite, garden_m2, user_notes
        FROM properties
        WHERE {where_sql}
        ORDER BY {order_column} {order_dir}
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [length, start])
    rows = cursor.fetchall()

    # DataTables formátum
    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "email_id": row["email_id"],
            "email_date": row["email_date"],
            "portal": row["portal"],
            "city": row["city"],
            "region": row["region"],
            "airport": row["airport"],
            "airport_km": row["airport_km"],
            "sea_km": row["sea_km"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "price_eur": row["price_eur"],
            "size_m2": row["size_m2"],
            "parking": row["parking"],
            "garden": row["garden"],
            "score": row["score"],
            "legal_status": row["legal_status"],
            "reason": row["reason"],
            "property_url": row["property_url"],
            "gmail_url": row["gmail_url"],
            "maps_url": row["maps_url"],
            "is_archived": row["is_archived"],
            "is_favorite": row["is_favorite"],
            "garden_m2": row["garden_m2"],
            "user_notes": row["user_notes"],
        })

    conn.close()

    return jsonify({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": filtered_records,
        "data": data,
    })


@app.route("/api/stats")
def api_stats():
    """Statisztikák a dashboard tetejére."""
    conn = get_db()
    cursor = conn.cursor()

    stats = {}

    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_archived = 0")
    stats["total"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM properties WHERE score >= 7 AND is_archived = 0")
    stats["high_score"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_favorite = 1 AND is_archived = 0")
    stats["favorites"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT region, COUNT(*) as count
        FROM properties
        WHERE is_archived = 0
        GROUP BY region
        ORDER BY count DESC
    """)
    stats["by_region"] = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return jsonify(stats)


@app.route("/api/properties/<int:prop_id>")
def api_get_property(prop_id):
    """Egy ingatlan lekérdezése szerkesztéshez."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE id = ?", (prop_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify(dict(row))


@app.route("/api/properties/<int:prop_id>", methods=["PUT"])
def api_update_property(prop_id):
    """Ingatlan szerkesztése (garden_m2, user_notes)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    allowed_fields = {"garden_m2", "user_notes"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"error": "No valid fields"}), 400

    conn = get_db()
    cursor = conn.cursor()

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [prop_id]

    cursor.execute(f"UPDATE properties SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        return jsonify({"error": "Not found"}), 404

    return jsonify({"success": True})


@app.route("/api/properties/<int:prop_id>/favorite", methods=["POST"])
def api_toggle_favorite(prop_id):
    """Kedvenc státusz váltása."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_favorite FROM properties WHERE id = ?", (prop_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    new_value = 0 if row["is_favorite"] else 1
    cursor.execute("UPDATE properties SET is_favorite = ? WHERE id = ?", (new_value, prop_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "is_favorite": new_value})


@app.route("/api/properties/<int:prop_id>/archive", methods=["POST"])
def api_toggle_archive(prop_id):
    """Archiválás váltása."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_archived FROM properties WHERE id = ?", (prop_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    new_value = 0 if row["is_archived"] else 1
    cursor.execute("UPDATE properties SET is_archived = ? WHERE id = ?", (new_value, prop_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "is_archived": new_value})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
