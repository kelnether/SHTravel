```python
import subprocess  # �9�8 ���������ⲿ Python �ļ�
import sys

import bcrypt
import pymysql
from flask import Flask, redirect, url_for, render_template, request, jsonify, session

from ai_recommendation import generate_recommendation
from analysis import analysis_bp
from bigdata import bigdata_bp

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Flask session


# �9�8 ���� MySQL
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="123456",
        database="ctrip_data",
        charset="utf8mb4"
    )


# ȷ�� Python ������ʹ�� UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

app.register_blueprint(bigdata_bp)
app.register_blueprint(analysis_bp)


# �9�8 1. ֱ������ Neo4j ��� Python �ļ�
def run_script(script_name):
    try:
        result = subprocess.run(["python", script_name], capture_output=True, text=True, check=True)
        print(f"�7�3 ���� {script_name} �ɹ�")
        return result.stdout  # ��ȡ�ű����ؽ��
    except subprocess.CalledProcessError as e:
        print(f"�7�4 ���� {script_name} ʧ��: {e}")
        return None


@app.context_processor
def inject_logged_in():
    return dict(logged_in=("user_id" in session))


# �9�8 2. ��ҳ������������
@app.route('/')
def index_tem():
    return redirect('http://localhost:3001/#/index')


'''
def index():
    return render_template("index.html", logged_in="user_id" in session)
'''


@app.route('/index_vue')
def index_vue():
    return render_template("index_vue.html", logged_in="user_id" in session)


# �9�8 3. ��Ⱦע��ҳ��
@app.route('/register')
def register_page():
    return render_template("register.html")


@app.route('/register_api', methods=['POST'])
def register_api():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    preferences = data.get("preferences")  # ȷ�����յ����б�

    if not username or not password or not preferences:
        return jsonify({"error": "�û����������ƫ�ò���Ϊ��"}), 400

    # �9�8 ��������
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # **1. �����û���Ϣ**
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()

        # **2. ��ȡ�û� ID**
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cursor.fetchone()[0]

        # **3. ȷ�� `preferences` Ϊ�б�**
        if isinstance(preferences, str):
            preferences = [preferences]  # ����ǵ���ֵ��ת��Ϊ�б�

        # **4. �����û�ƫ�ã��������ݣ�**
        for category in preferences:
            cursor.execute("INSERT INTO user_preferences (user_id, category) VALUES (%s, %s)", (user_id, category))

        conn.commit()
    except pymysql.IntegrityError:
        return jsonify({"error": "�7�4 �û����Ѵ��ڣ�"}), 409
    finally:
        cursor.close()
        conn.close()

    print(f"�7�3 �û� {username} ע��ɹ���ƫ�����: {preferences}")

    # **5. ����ͬ���ű�����ƫ�ô��� Neo4j**
    run_script("recommendation_KG/sync_user_preferences_to_neo4j.py")

    return jsonify({"message": "�7�3 ע��ɹ���"}), 201


# �9�8 4. ��Ⱦ��¼ҳ��
@app.route('/login')
def login_page():
    return render_template("login.html")


@app.route('/login_api', methods=['POST'])
def login_api():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "�û��������벻��Ϊ��"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
        session["user_id"] = user[0]
        return jsonify({"message": "�7�3 ��¼�ɹ���", "user_id": user[0]}), 200
    else:
        return jsonify({"error": "�7�4 �û������������"}), 401


# �9�8 5. �����û��ǳ�
@app.route('/logout')
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


# �9�8 6. ��Ⱦ����ҳ�棨����¼�û��ɷ��ʣ�
@app.route('/search', methods=['GET'])
def search_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    # �� URL ��ѯ�����л�ȡ��������
    poiName = request.args.get("poiName", "").strip()

    # ������ڲ�ѯ���ݣ����������
    if poiName:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT poiName, sightCategoryInfo, commentScore, coverImageUrl 
            FROM attractions 
            WHERE poiName LIKE %s 
            LIMIT 5;
        """
        cursor.execute(query, (f"%{poiName}%",))
        spot_info_list = cursor.fetchall()
        cursor.close()
        conn.close()
        # ��Ⱦģ��ʱ����ѯ�����ͽ������
        return render_template("search.html", poiName=poiName, results=spot_info_list)
    else:
        # û�в�ѯ���ݣ���ʾ�հ׵�����ҳ��
        return render_template("search.html", results=[])


# �9�8 7. �������� API����������������Ƽ�
@app.route('/search_api', methods=['POST'])
def search_api():
    if "user_id" not in session:
        return jsonify({"error": "δ��¼�û��޷�������"}), 403

    data = request.get_json()
    user_id = session["user_id"]
    poiName = data.get("poiName").strip()  # ȥ��ǰ��ո�

    if not poiName:
        return jsonify({"error": "�����뾰������"}), 400

    print(f"�9�3 �û� {user_id} ��������: {poiName}")  # Debug ���

    conn = get_db_connection()
    cursor = conn.cursor()

    # **1. ��¼������ʷ**
    insert_sql = """
    INSERT INTO user_visits (user_id, poiName)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE poiName=VALUES(poiName);
    """
    cursor.execute(insert_sql, (user_id, poiName))
    conn.commit()

    # **2. ����ģ����ѯ**
    select_sql = """
    SELECT poiName, sightCategoryInfo, commentScore, coverImageUrl, id 
    FROM attractions 
    WHERE poiName LIKE %s 
    LIMIT 5;
    """
    cursor.execute(select_sql, (f"%{poiName}%",))
    spot_info_list = cursor.fetchall()
    cursor.close()
    conn.close()

    # **3. �����ⲿ�Ƽ��ű�**
    run_script("recommendation_KG/sync_user_search_to_neo4j.py")  # ����������ʷ
    recommendation_output = run_script("recommendation_KG/recommend_attractions.py")  # ��ȡ�Ƽ��б�

    # **4. �����Ƽ�����**
    recommended_spots = []
    if recommendation_output:
        lines = recommendation_output.split("\n")
        for line in lines:
            if "�7�3 Ϊ" in line and "�Ƽ��ľ���" in line:
                raw_list = line.split("��")[-1].strip()
                try:
                    recommended_spots = eval(raw_list)  # ������ Python �б�
                except Exception as e:
                    print("�7�4 �����Ƽ��б�ʧ��", e)
                break

    recommended_spot_names = [spot[0] for spot in recommended_spots]  # ��ȡ��������

    # **5. �����ݿ��ȡ�Ƽ�����������Ϣ**
    conn = get_db_connection()
    cursor = conn.cursor()
    recommendations_info = []

    if recommended_spot_names:
        placeholders = ', '.join(['%s'] * len(recommended_spot_names))  # ���� SQL �﷨
        query = f"""
        SELECT poiName, sightCategoryInfo, commentScore, coverImageUrl, id 
        FROM attractions 
        WHERE poiName IN ({placeholders});
        """
        cursor.execute(query, tuple(recommended_spot_names))
        recommendations_info = cursor.fetchall()

    cursor.close()
    conn.close()

    # **6. ���� JSON ���**
    return jsonify({
        "message": f"�7�3 �����ɹ����ҵ� {len(spot_info_list)} ����ؾ��㡣",
        "found": bool(spot_info_list),
        "spots": [
            {
                "name": spot[0],
                "category": spot[1],
                "score": spot[2],
                "image": spot[3],
                "id": spot[4]
            }
            for spot in spot_info_list
        ],
        "recommendations": [
            {
                "name": rec[0],
                "category": rec[1],
                "score": rec[2],
                "image": rec[3],
                "id": rec[4]
            }
            for rec in recommendations_info
        ]
    }), 200


# ����� app.py ����������·�ɣ�
@app.route('/recommendations')
def recommendations_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("recommendations.html")


# �9�8 7.1 ����Ƽ�ӳ�� API�������Ƽ�ҳ����ã�
@app.route('/recommendations_api', methods=['POST'])
def recommendations_api():
    if "user_id" not in session:
        return jsonify({"error": "δ��¼�û��޷���ȡ�Ƽ���"}), 403

    user_id = session["user_id"]

    # �����Ƽ��ű���ȡ�Ƽ��б�
    recommendation_output = run_script("recommendation_KG/recommend_attractions.py")

    recommended_spots = []
    if recommendation_output:
        lines = recommendation_output.split("\n")
        for line in lines:
            if "�7�3 Ϊ" in line and "�Ƽ��ľ���" in line:
                raw_list = line.split("��")[-1].strip()
                try:
                    recommended_spots = eval(raw_list)
                except Exception as e:
                    print("�7�4 �����Ƽ��б�ʧ��", e)
                break

    recommended_spot_names = [spot[0] for spot in recommended_spots]

    # �����ݿ��ȡ�Ƽ�����������Ϣ
    conn = get_db_connection()
    cursor = conn.cursor()
    recommendations_info = []
    if recommended_spot_names:
        placeholders = ', '.join(['%s'] * len(recommended_spot_names))
        query = f"""
        SELECT poiName, sightCategoryInfo, commentScore, coverImageUrl, id
        FROM attractions
        WHERE poiName IN ({placeholders});
        """
        cursor.execute(query, tuple(recommended_spot_names))
        recommendations_info = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        "recommendations": [
            {
                "name": rec[0],
                "category": rec[1],
                "score": rec[2],
                "image": rec[3],
                "id": rec[4]
            }
            for rec in recommendations_info
        ]
    }), 200


# �9�8 8. ��������ҳ��
@app.route("/attraction/<int:spot_id>")
def attraction_page(spot_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT id, poiName, sightCategoryInfo, commentScore, coverImageUrl, description
        FROM attractions 
        WHERE id = %s 
        LIMIT 1
    """
    cursor.execute(query, (spot_id,))
    spot_info = cursor.fetchone()
    cursor.close()
    conn.close()

    if not spot_info:
        return "�7�4 ������Ϣδ�ҵ���", 404

    attraction_data = {
        "id": spot_info[0],
        "name": spot_info[1],
        "category": spot_info[2],
        "score": spot_info[3],
        "image": spot_info[4],
        "description": spot_info[5] or "���޽��ܡ�"
    }

    return render_template("attraction.html", attraction=attraction_data)


# ��Ⱦ����ҳ��
# �9�8 ��������Ⱦ AI �Ƽ�ҳ��
@app.route('/recommendation_ai')
def recommendation_ai_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("recommendation_ai.html")


# �9�8 ���������� AI �Ƽ� API ����
@app.route('/recommendation_ai_api', methods=['POST'])
def recommendation_ai_api():
    if "user_id" not in session:
        return jsonify({"error": "δ��¼�û��޷������Ƽ���"}), 403

    data = request.get_json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "��ʾ����Ϊ�գ�"}), 400

    # ���� AI ���������Ƽ�
    recommendation = generate_recommendation(prompt)
    return jsonify({"recommendation": recommendation}), 200


def get_user_preferences_from_mysql(user_id):
    """�� MySQL ��ѯ�û�ƫ�ã�������ƫ����صĽڵ�ͱ�"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category FROM user_preferences WHERE user_id = %s", (user_id,))
    preferences = cursor.fetchall()
    cursor.close()
    conn.close()

    nodes = []
    edges = []
    for row in preferences:
        category = row[0]
        cat_node_id = f"cat_{category}"
        # �����ظ������ͬ���ڵ�
        if not any(n["data"]["id"] == cat_node_id for n in nodes):
            nodes.append({"data": {"id": cat_node_id, "label": category}})
        edges.append({
            "data": {
                "id": f"user_{user_id}_{cat_node_id}",
                "source": f"user_{user_id}",
                "target": cat_node_id
            }
        })
    return nodes, edges

def get_user_searches_from_mysql(user_id):
    """�� MySQL ��ѯ�û�������¼��������������¼��صĽڵ�ͱ�"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT poiName FROM user_visits WHERE user_id = %s", (user_id,))
    searches = cursor.fetchall()
    cursor.close()
    conn.close()

    nodes = []
    edges = []
    for row in searches:
        poi = row[0]
        poi_node_id = f"poi_{poi}"
        # �����ظ������ͬ����ڵ�
        if not any(n["data"]["id"] == poi_node_id for n in nodes):
            nodes.append({"data": {"id": poi_node_id, "label": poi}})
        edges.append({
            "data": {
                "id": f"user_{user_id}_{poi_node_id}",
                "source": f"user_{user_id}",
                "target": poi_node_id
            }
        })
    return nodes, edges


@app.route('/profile')
def profile():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    user_id = session["user_id"]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # ��ȡ�û�������Ϣ������ id, username, password��
        cursor.execute(
            "SELECT id, username, password FROM users WHERE id = %s",
            (user_id,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            cursor.close()
            conn.close()
            return "�û���Ϣ������", 404

        # �������ݿ���û�� email��registration_date��avatar_url��bio �ֶΣ�����Ĭ��ֵ
        user_data = {
            "id": user_row[0],
            "username": user_row[1],
            "email": "δ�ṩ",  # Ĭ������
            "registration_date": "δ֪",  # Ĭ��ע������
            "avatar_url": "static/pic/HEIF Image.png",  # Ĭ��ͷ��·��
            "bio": "���޼��"  # Ĭ�ϸ��˼��
        }

        # -----------------------
        # 1. ��ȡ������¼(���ڡ��������ݡ�)
        # -----------------------
        # ������ user_visits ���е� poiName Ϊ�û��������ľ���ؼ���
        cursor.execute(
            "SELECT poiName FROM user_visits WHERE user_id = %s ORDER BY id DESC LIMIT 20",
            (user_id,)
        )
        visits = cursor.fetchall() or []
        # �������ؼ�����ȡ��������ǰ�˵�����չʾ
        user_data["search_history"] = [row[0] for row in visits]

        # -----------------------
        # 2. ��ȡ������̬��Ϣ(�Ҳ���ʾ)
        # -----------------------
        # Ҳ����ֱ�Ӹ�������� visits ����
        # ����ʾ������ǰ 10 ����¼���������̬��
        user_data["activities"] = [
            {"description": "�������㣺" + row[0]}
            for row in visits[:10]
        ]

        # ����оɵ� favorites �ȣ�Ҳ���ڴ˴�����Ϊ�ջ������ݿ��в�ѯ
        user_data["favorites"] = []

        # �����Ҫ֪ʶͼ������
        graph_preferences = get_user_preferences_from_mysql(user_id)
        graph_searches = get_user_searches_from_mysql(user_id)

    except Exception as e:
        print("Error loading profile:", e)
        return "�������ڲ�����", 500
    finally:
        cursor.close()
        conn.close()

    print(graph_preferences)
    print(graph_searches)

    # ����Ⱦģ��ʱ���� search_history ����ǰ��
    return render_template(
        "profile.html",
        user=user_data,
        graph_preferences=graph_preferences,
        graph_searches=graph_searches
    )

if __name__ == '__main__':
    app.run(debug=True)
```