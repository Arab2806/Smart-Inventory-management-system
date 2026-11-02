
import os
from dotenv import load_dotenv

load_dotenv()
from flask import Flask, request, jsonify, send_from_directory
import mysql.connector

app = Flask(__name__)


# DATABASE CONNECTION
def get_db():
    return mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
    )


# HOME PAGE
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


# GET ALL CATEGORIES
@app.route("/api/categories", methods=["GET"])
def get_categories():
    con = get_db()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT * FROM Category ORDER BY category_id")
    data = cur.fetchall()

    cur.close()
    con.close()

    return jsonify(data)


# ADD CATEGORY
@app.route("/api/categories", methods=["POST"])
def add_category():
    d = request.json
    con = get_db()
    cur = con.cursor()

    try:
        cur.execute(
            "INSERT INTO Category VALUES (%s, %s)",
            (d["category_id"], d["category_name"])
        )
        con.commit()
        return jsonify({"message": "Category added successfully!"})

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        con.close()


# GET ALL SUPPLIERS
@app.route("/api/suppliers", methods=["GET"])
def get_suppliers():
    con = get_db()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT * FROM Supplier ORDER BY supplier_id")
    data = cur.fetchall()

    cur.close()
    con.close()

    return jsonify(data)


# ADD SUPPLIER
@app.route("/api/suppliers", methods=["POST"])
def add_supplier():
    d = request.json
    con = get_db()
    cur = con.cursor()

    try:
        cur.execute("""
            INSERT INTO Supplier (supplier_id, supplier_name, phone, email)
            VALUES (%s, %s, %s, %s)
        """, (
            d["supplier_id"], d["supplier_name"],
            d.get("phone"), d.get("email")
        ))

        con.commit()
        return jsonify({"message": "Supplier added successfully!"})

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        con.close()


# DELETE SUPPLIER
@app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
def delete_supplier(supplier_id):
    con = get_db()
    cur = con.cursor()

    try:
        cur.execute(
            "SELECT COUNT(*) FROM Product WHERE supplier_id = %s",
            (supplier_id,)
        )

        count = cur.fetchone()[0]

        if count:
            return jsonify({
                "error": "Cannot delete supplier because products are linked."
            }), 400

        cur.execute(
            "DELETE FROM Supplier WHERE supplier_id = %s",
            (supplier_id,)
        )

        if cur.rowcount == 0:
            return jsonify({"error": "Supplier not found"}), 404

        con.commit()
        return jsonify({"message": "Supplier deleted successfully!"})

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        con.close()


# GET ALL PRODUCTS
@app.route("/api/products", methods=["GET"])
def get_products():
    con = get_db()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT p.product_id, p.product_name, p.category_id, p.supplier_id,
               p.price, p.quantity, p.minimum_stock,
               c.category_name, s.supplier_name
        FROM Product p
        LEFT JOIN Category c ON p.category_id = c.category_id
        LEFT JOIN Supplier s ON p.supplier_id = s.supplier_id
        ORDER BY p.product_id
    """)

    data = cur.fetchall()

    for p in data:
        p["price"] = float(p["price"]) if p["price"] is not None else 0

    cur.close()
    con.close()

    return jsonify(data)


# ADD PRODUCT
@app.route("/api/products", methods=["POST"])
def add_product():
    d = request.json
    con = get_db()
    cur = con.cursor()

    try:
        cur.execute("""
            INSERT INTO Product
            (product_id, product_name, category_id, supplier_id,
             price, quantity, minimum_stock)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            d["product_id"], d["product_name"],
            d["category_id"], d["supplier_id"],
            d["price"], d["quantity"], d["minimum_stock"]
        ))

        con.commit()
        return jsonify({"message": "Product added successfully!"})

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        con.close()


# UPDATE PRODUCT
@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    d = request.json
    con = get_db()
    cur = con.cursor()

    try:
        cur.execute("""
            UPDATE Product
            SET product_name=%s, category_id=%s, supplier_id=%s,
                price=%s, quantity=%s, minimum_stock=%s
            WHERE product_id=%s
        """, (
            d["product_name"], d["category_id"],
            d["supplier_id"], d["price"],
            d["quantity"], d["minimum_stock"],
            product_id
        ))

        if cur.rowcount == 0:
            cur.execute(
                "SELECT product_id FROM Product WHERE product_id=%s",
                (product_id,)
            )

            if cur.fetchone() is None:
                return jsonify({"error": "Product not found"}), 404

        con.commit()
        return jsonify({"message": "Product updated successfully!"})

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        con.close()


# DELETE PRODUCT
@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    con = get_db()
    cur = con.cursor()

    try:
        cur.execute(
            "DELETE FROM Product WHERE product_id=%s",
            (product_id,)
        )

        if cur.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404

        con.commit()
        return jsonify({"message": "Product deleted successfully!"})

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        con.close()


# STOCK IN AND STOCK OUT
@app.route("/api/stock", methods=["POST"])
def update_stock():
    d = request.json

    product_id = d["product_id"]
    quantity = d["quantity"]
    action = d["action"]

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "Enter a valid quantity"}), 400

    if action not in ("in", "out"):
        return jsonify({"error": "Invalid stock action"}), 400

    con = get_db()
    cur = con.cursor()

    try:
        cur.execute(
            "SELECT quantity FROM Product WHERE product_id=%s",
            (product_id,)
        )

        result = cur.fetchone()

        if result is None:
            return jsonify({"error": "Product not found"}), 404

        current = result[0]

        if action == "out" and quantity > current:
            return jsonify({"error": "Not enough stock available"}), 400

        if action == "in":
            new_quantity = current + quantity
        else:
            new_quantity = current - quantity

        cur.execute(
            "UPDATE Product SET quantity=%s WHERE product_id=%s",
            (new_quantity, product_id)
        )

        con.commit()

        return jsonify({
            "message": "Stock updated successfully!",
            "new_quantity": new_quantity
        })

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        con.close()


# START FLASK SERVER
if __name__ == "__main__":
    app.run(debug=True)
