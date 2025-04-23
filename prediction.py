# prediction.py
from flask import Blueprint, render_template, jsonify, request
import os
import pandas as pd

prediction_bp = Blueprint('prediction', __name__, url_prefix='/prediction',
                          template_folder='templates', static_folder='static')


def load_prediction_data():
    """
    从目录 visitors_flowrate_pred_arima/csv_predictions 加载预测数据，
    每个 CSV 文件对应一个景点的 24 小时预测数据，返回字典：
       键：景点名称（从 CSV 文件名中提取，不包含扩展名；若文件名含有点号，则取最后一部分）
       值：对应的 DataFrame（会转换 datetime 列提取 hour，并把 predicted_visitors 重命名为 visitor_count）

    CSV 示例数据：
    datetime,predicted_visitors
    2018-07-01 07:11:00,56.52468298383235
    """
    current_dir = os.path.dirname(__file__)
    csv_folder = os.path.join(current_dir, 'visitors_flowrate_pred_arima', 'csv_predictions')
    if not os.path.exists(csv_folder):
        raise Exception("找不到预测数据目录：{}".format(csv_folder))
    prediction_data = {}
    for file_name in os.listdir(csv_folder):
        if file_name.lower().endswith('.csv'):
            # 从文件名中去除扩展名并处理，如 "1.东方假日" 取最后一部分作为景点名称
            scenic_name = os.path.splitext(file_name)[0].strip()
            if '.' in scenic_name:
                parts = scenic_name.split('.')
                scenic_name = parts[-1].strip()
            file_path = os.path.join(csv_folder, file_name)
            df = pd.read_csv(file_path)
            # 标准化列名
            df.columns = [col.strip().lower() for col in df.columns]
            # 将 datetime 列转换为 Pandas datetime，同时指定格式并设置 errors='coerce'
            df["datetime"] = pd.to_datetime(df["datetime"],
                                            format='%Y-%m-%d %H:%M:%S',
                                            errors='coerce')
            # 丢弃无法解析的行
            df = df.dropna(subset=["datetime"])
            # 提取小时信息
            df["hour"] = df["datetime"].dt.hour
            # 重命名 predicted_visitors 为 visitor_count
            if "predicted_visitors" in df.columns:
                df = df.rename(columns={"predicted_visitors": "visitor_count"})
            else:
                raise Exception(f"CSV文件 {file_name} 缺少 'predicted_visitors' 列")
            prediction_data[scenic_name] = df
    return prediction_data


# 加载所有景点的预测数据（不合并，每个 CSV 对应一个景点）
prediction_data_dict = load_prediction_data()


@prediction_bp.route('/')
def index():
    """渲染预测数据展示页面"""
    return render_template('predictions.html')


@prediction_bp.route('/api/scenic_names', methods=['GET'])
def get_scenic_names():
    """返回所有景点名称列表（从 CSV 文件名中提取）"""
    scenic_names = list(prediction_data_dict.keys())
    return jsonify(scenic_names)


@prediction_bp.route('/api/prediction', methods=['GET'])
def get_prediction():
    """
    返回指定景点的预测数据（24小时），数据按 hour 排序。
    请求参数：
      - scenic：景点名称（必填）
    """
    scenic = request.args.get('scenic')
    if not scenic:
        return jsonify({"error": "参数 scenic 是必需的"}), 400
    if scenic not in prediction_data_dict:
        return jsonify({"error": f"未找到景点 {scenic} 的预测数据"}), 404
    df = prediction_data_dict[scenic]
    df = df.sort_values(by='hour')
    return jsonify(df.to_dict(orient='records'))
