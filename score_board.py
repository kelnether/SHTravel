import pymysql
import pandas as pd

# �������ݿ�����
conn = pymysql.connect(host='localhost', user='user', password='password', db='your_db', charset='utf8mb4')

# ��ѯ����
query = "SELECT id, city, poiName, sightLevelStr, commentScore, heatScore, maxCapacity, trafficAccessibility FROM attractions"
df = pd.read_sql(query, conn)

# �ر����ݿ�����
conn.close()

# �����ȼ�ת������
def convert_sight_level(level):
    mapping = {'5A': 100, '4A': 80, '3A': 60, '2A': 40, '1A': 20}
    return mapping.get(level, 0)

# Ӧ��ת������
df['sightLevelScore'] = df['sightLevelStr'].apply(convert_sight_level)
# ָ���׼�������û����֡�������������ͨͨ��ȣ�
df['userScore'] = df['commentScore'] / 5.0 * 100  # �û��������5.0��׼����100
df['historicalVisitorFlowScore'] = df['heatScore']
df['capacityScore'] = (df['maxCapacity'] / df['maxCapacity'].max()) * 100
df['trafficScore'] = (df['trafficAccessibility'] / df['trafficAccessibility'].max()) * 100

# �����ۺ��ȶȵ÷�
df['comprehensiveHeatScore'] = (
    df['sightLevelScore'] * 0.30 +
    df['userScore'] * 0.25 +
    df['historicalVisitorFlowScore'] * 0.20 +
    df['capacityScore'] * 0.15 +
    df['trafficScore'] * 0.10
)

# ��ʾ���
print(df[['id', 'city', 'poiName', 'comprehensiveHeatScore']])
