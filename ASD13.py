import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
import folium
from streamlit_folium import folium_static
from io import BytesIO

# 🔹 **المسارات الأساسية**
data_frame_template_path = "The data frame file to be analyzed.xlsx"
coordinates_path = "Meter_Locations_Database.xlsx"
model_path = "ASD12_XGBoost.pkl"

# 🔹 **تحميل ملف الإحداثيات العام**
def load_coordinates():
    try:
        return pd.read_excel(coordinates_path)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Meter Number", "Latitude", "Longitude"])

# 🔹 **إضافة تفسير واضح لحالات الفاقد**
def add_loss_reason(row):
    if row['V1'] == 0 and row['A1'] > 0:
        return '⚠️ فقد بسبب جهد صفر وتيار على V1'
    elif row['V2'] == 0 and row['A2'] > 0:
        return '⚠️ فقد بسبب جهد صفر وتيار على V2'
    elif row['V3'] == 0 and row['A3'] > 0:
        return '⚠️ فقد بسبب جهد صفر وتيار على V3'
    elif row['V1'] < 50 and row['A1'] > 0:
        return '⚠️ فقد محتمل بسبب جهد منخفض جدًا على V1'
    elif row['V2'] < 50 and row['A2'] > 0:
        return '⚠️ فقد محتمل بسبب جهد منخفض جدًا على V2'
    elif row['V3'] < 50 and row['A3'] > 0:
        return '⚠️ فقد محتمل بسبب جهد منخفض جدًا على V3'
    elif row['V1'] == 0 and abs(row['A2'] - row['A3']) > 0.6 * max(row['A2'], row['A3']):
        return '⚠️ فقد محتمل بسبب عدم توازن التيار بين A2 و A3 مع جهد صفر على V1'
    elif row['V2'] == 0 and abs(row['A1'] - row['A3']) > 0.6 * max(row['A1'], row['A3']):
        return '⚠️ فقد محتمل بسبب عدم توازن التيار بين A1 و A3 مع جهد صفر على V2'
    elif row['V3'] == 0 and abs(row['A1'] - row['A2']) > 0.6 * max(row['A1'], row['A2']):
        return '⚠️ فقد محتمل بسبب عدم توازن التيار بين A1 و A2 مع جهد صفر على V3'
    else:
        return '✅ لا توجد حالة فقد مؤكدة'

# 🔹 **تحليل البيانات**
def analyze_data(data):
    try:
        model = joblib.load(model_path)
        required_columns = ["Meter Number", "V1", "V2", "V3", "A1", "A2", "A3"]
        
        if not set(required_columns).issubset(data.columns):
            st.error("⚠️ الملف لا يحتوي على الأعمدة المطلوبة للتحليل!")
            return

        X = data[["V1", "V2", "V3", "A1", "A2", "A3"]]
        predictions = model.predict(X)
        data["Predicted_Loss"] = predictions

        # 🔹 **تصنيف الأولوية بناءً على الشروط المحددة**
        def classify_priority(row):
            if row["Predicted_Loss"] == 1 and (
                row["V1"] == 0 and row["A1"] > 0 or 
                row["V2"] == 0 and row["A2"] > 0 or 
                row["V3"] == 0 and row["A3"] > 0 or
                row["V1"] < 50 and row["A1"] > 0 or
                row["V2"] < 50 and row["A2"] > 0 or
                row["V3"] < 50 and row["A3"] > 0 or
                row["V1"] == 0 and abs(row["A2"] - row["A3"]) > 0.6 * max(row["A2"], row["A3"]) or
                row["V2"] == 0 and abs(row["A1"] - row["A3"]) > 0.6 * max(row["A1"], row["A3"]) or
                row["V3"] == 0 and abs(row["A1"] - row["A2"]) > 0.6 * max(row["A1"], row["A2"])
            ):
                return "High"
            else:
                return "Normal"

        data["Priority"] = data.apply(classify_priority, axis=1)
        data["Loss_Reason"] = data.apply(add_loss_reason, axis=1)

        # 🔹 **إضافة الإحداثيات للعدادات ذات الفاقد**
        coords_df = load_coordinates()
        data = data.merge(coords_df, on="Meter Number", how="left")

        return data

    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء تحليل البيانات: {str(e)}")
        return None

# 📂 **إضافة خيار تحميل قالب البيانات (الفريم وورك)**
st.sidebar.title("📂 تحميل قالب البيانات")
with open(data_frame_template_path, "rb") as template_file:
    st.sidebar.download_button(
        label="📥 تحميل قالب البيانات",
        data=template_file,
        file_name="The_data_frame_file_to_be_analyzed.xlsx"
    )

# 📥 **رفع ملف البيانات للتحليل**
st.subheader("📊 نظام اكتشاف حالات الفاقد المحتملة ")
uploaded_file = st.file_uploader("📤 قم برفع ملف البيانات للتحليل (Excel)", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    analyzed_data = analyze_data(df)

    if analyzed_data is not None:
        st.subheader("📋 جميع حالات الفاقد المكتشفة")
        st.dataframe(analyzed_data)

# 🏷️ **إضافة معلومات المطور**
st.markdown("---")
st.markdown("👨‍💻 **المطور: مشهور العباس-78598-00966553339838** | 📅 **تاريخ التحديث:** 08-03-2025")
