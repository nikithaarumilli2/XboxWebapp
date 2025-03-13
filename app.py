from flask import Flask, render_template, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-metadata', methods=['POST'])
def get_metadata():
    title_name = request.form['titleName']
    product_id = request.form['productId']
    print(f"Received: title_name={title_name}, product_id={product_id}")

    # Databricks API details
    url = "https://adb-587320870163884.4.azuredatabricks.net/api/2.0/sql/statements"
    token = "dapi077888329943fcf7e5f882252378fa09-3"

    sql_query = f"SELECT ProductID, Title, ReleaseDate, Avg_Rating, Available_On, Categories, Descriptions, Publisher_Name, Included_With, Addons, Content_Rating FROM vw_xbox_data WHERE title = '{title_name}' AND productid = '{product_id}' LIMIT 1"
    print(f"Executing query: {sql_query}")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "warehouse_id": "c0d56c817655d9c9",
        "catalog": "xbox_catalog",
        "schema": "dbo",
        "statement": sql_query
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch data", "message": response.text}), response.status_code

@app.route('/add-record', methods=['POST'])
def add_record():
    data = request.get_json()
    print(f"Received data for insertion: {data}")

    # Databricks API details
    url = "https://adb-587320870163884.4.azuredatabricks.net/api/2.0/sql/statements"
    token = "dapi077888329943fcf7e5f882252378fa09-3"

    product_id = data['productId']
    check_query = f"SELECT COUNT(*) FROM game_details WHERE productid = '{product_id}'"
    print(f"Executing query: {check_query}")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "warehouse_id": "c0d56c817655d9c9",
        "catalog": "xbox_catalog",
        "schema": "dbo",
        "statement": check_query
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to check product ID", "message": response.text}), response.status_code

    result = response.json()
    print(f"Result from count query: {result}")

    count = result['data'][0][0] if 'data' in result else 0

    print(count)

    if count > 0:
        # Update record
        update_query = f"UPDATE game_details SET " + ", ".join([f"{k}='{v}'" for k, v in data.items() if k != 'productId']) + f" WHERE productid='{product_id}'"
        print(f"Executing update query: {update_query}")

        payload['statement'] = update_query
    else:
        # Insert new record
        columns = ", ".join(data.keys())
        values = ", ".join(f"'{v}'" for v in data.values())
        insert_query = f"INSERT INTO game_details ({columns}) VALUES ({values})"
        print(f"Executing insert query: {insert_query}")

        payload['statement'] = insert_query

    response = requests.post(url, headers=headers, json=payload)
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        return jsonify({"message": "Record processed successfully"})
    else:
        return jsonify({"error": "Failed to process record", "message": response.text}), response.status_code

@app.route('/delete-record', methods=['POST'])
def delete_record():
    data = request.get_json()
    product_id = data['productId']
    print(f"Received request to delete record with Product ID: {product_id}")

    # Databricks API details
    url = "https://adb-587320870163884.4.azuredatabricks.net/api/2.0/sql/statements"
    token = "dapi077888329943fcf7e5f882252378fa09-3"

    fetch_query = f"SELECT * FROM game_details WHERE productid = '{product_id}'"
    delete_query = f"DELETE FROM game_details WHERE productid = '{product_id}'"
    print(f"Executing fetch query: {fetch_query}")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "warehouse_id": "c0d56c817655d9c9",
        "catalog": "xbox_catalog",
        "schema": "dbo",
        "statement": fetch_query
    }

    fetch_response = requests.post(url, headers=headers, json=payload)
    print(f"Fetch response status: {fetch_response.status_code}")
    if fetch_response.status_code != 200:
        return jsonify({"error": "Failed to fetch record", "message": fetch_response.text}), fetch_response.status_code

    fetch_result = fetch_response.json()
    print(f"Result from fetch query: {fetch_result}")

    if 'data' not in fetch_result or not fetch_result['data']:
        return jsonify({"message": "No record found with the given Product ID"}), 404

    deleted_record = fetch_result['data'][0]

    payload['statement'] = delete_query
    print(f"Executing delete query: {delete_query}")

    delete_response = requests.post(url, headers=headers, json=payload)
    print(f"Delete response status: {delete_response.status_code}")
    if delete_response.status_code == 200:
        return jsonify({"message": "Record deleted successfully", "deleted_record": deleted_record})
    else:
        return jsonify({"error": "Failed to delete record", "message": delete_response.text}), delete_response.status_code

@app.route('/apply-filters', methods=['POST'])
def apply_filters():
    filters = request.get_json()
    rating_filter = filters['rating']
    genres_filter = filters['genres']
    platform_filter = filters['platform']
    sort_by = filters['sortBy']

    # Building the SQL query
    conditions = []
    if rating_filter == "3_and_above":
        conditions.append("Avg_Rating >= 3")
    elif rating_filter == "below_3":
        conditions.append("Avg_Rating < 3")

    if genres_filter:
        genre_conditions = " OR ".join([f"Categories LIKE '%{genre}%'" for genre in genres_filter])
        conditions.append(f"({genre_conditions})")

    if platform_filter:
        conditions.append(f"Available_On LIKE '%{platform_filter}%'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql_query = f"SELECT ProductID, Title, ReleaseDate, Avg_Rating, Available_On, Categories, Descriptions, Publisher_Name, Included_With, Addons, Content_Rating FROM vw_xbox_data WHERE {where_clause} ORDER BY {sort_by}"
    print(f"Executing filter query: {sql_query}")

    # Databricks API details
    url = "https://adb-587320870163884.4.azuredatabricks.net/api/2.0/sql/statements"
    token = "dapi077888329943fcf7e5f882252378fa09-3"

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "warehouse_id": "c0d56c817655d9c9",
        "catalog": "xbox_catalog",
        "schema": "dbo",
        "statement": sql_query
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"Filter response status: {response.status_code}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to apply filters", "message": response.text}), response.status_code

    result = response.json()
    print(f"Result from filter query: {result}")

    if 'result' in result:
        return jsonify({"columns": result['manifest']['schema']['columns'], "result": result['result']['data_array']})
    else:
        return jsonify({"result": []})

@app.route('/get-product-catalog', methods=['GET'])
def get_product_catalog():
    # SQL query to fetch all data from the respective table
    sql_query = "SELECT * FROM vw_xbox_data"

    # Databricks API details
    url = "https://adb-587320870163884.4.azuredatabricks.net/api/2.0/sql/statements"
    token = "dapi077888329943fcf7e5f882252378fa09-3"

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "warehouse_id": "c0d56c817655d9c9",
        "catalog": "xbox_catalog",
        "schema": "dbo",
        "statement": sql_query
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"Product Catalog response status: {response.status_code}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch product catalog", "message": response.text}), response.status_code

    result = response.json()
    print(f"Result from product catalog query: {result}")

    if 'result' in result:
        return jsonify({"columns": result['manifest']['schema']['columns'], "result": result['result']['data_array']})
    else:
        return jsonify({"result": []})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
