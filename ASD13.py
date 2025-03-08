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
        return '⚠️ فقد مؤكد بسبب جهد صفر وتيار على V1'
    elif row['V1'] < 50 and row['A1'] > 0:
        return '⚠️ فقد محتمل بسبب جهد منخفض وتيار على V1'
    elif row['V2'] == 0 and row['A2'] > 0:
        return '⚠️ فقد مؤكد بسبب جهد صفر وتيار على V2'
    elif row['V2'] < 50 and row['A2'] > 0:
        return '⚠️ فقد محتمل بسبب جهد منخفض وتيار على V2'
    elif row['V3'] == 0 and row['A3'] > 0:
        return '⚠️ فقد مؤكد بسبب جهد صفر وتيار على V3'
    elif row['V3'] < 50 and row['A3'] > 0:
        return '⚠️ فقد محتمل بسبب جهد منخفض وتيار على V3'
    elif row['V1'] == 0 and abs(row['A2'] - row['A3']) > 0.6 * max(row['A2'], row['A3']):
        return '⚠️ فقد محتمل بسبب فرق تيار بين الفازات'
    elif row['V2'] == 0 and abs(row['A1'] - row['A3']) > 0.6 * max(row['A1'], row['A3']):
        return '⚠️ فقد محتمل بسبب فرق تيار بين الفازات'
    elif row['V3'] == 0 and abs(row['A1'] - row['A2']) > 0.6 * max(row['A1'], row['A2']):
        return '⚠️ فقد محتمل بسبب فرق تيار بين الفازات'
    else:
        return '✅ لا توجد حالة فقد مؤكدة'

# 🔹 **تحليل البيانات**
def analyze_data(data):
    try:
        model = joblib.load(model_path)
        required_columns = ["Meter Number", "V1", "V2", "V3", "A1", "A2", "A3"]
        
        if not set(required_columns).issubset(data.columns):
            st.error("⚠️ الملف لا يحتوي على الأعمدة المطلوبة للتحليل!")
            return None

        X = data[["V1", "V2", "V3", "A1", "A2", "A3"]]
        predictions = model.predict(X)
        data["Predicted_Loss"] = predictions
        data["Loss_Reason"] = data.apply(add_loss_reason, axis=1)
        data["Priority"] = data["Loss_Reason"].apply(lambda x: "High" if "⚠️" in str(x) else "Normal")

        # 🔹 **إضافة الإحداثيات للعدادات ذات الفاقد**
        coords_df = load_coordinates()
        data = data.merge(coords_df, on="Meter Number", how="left")

        return data
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء تحليل البيانات: {str(e)}")
        return None

# 📥 **رفع ملف البيانات للتحليل**
st.subheader("📊 نظام اكتشاف حالات الفاقد المحتملة ")
uploaded_file = st.file_uploader("📤 قم برفع ملف البيانات للتحليل (Excel)", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    high_priority_loss = analyze_data(df)
    if high_priority_loss is not None and not high_priority_loss.empty:
        st.subheader("📋 جميع حالات الفاقد ذات الأولوية العالية")
        st.dataframe(high_priority_loss)
        
        # 🌍 **عرض خريطة الفاقد**
        if "Latitude" in high_priority_loss.columns and "Longitude" in high_priority_loss.columns:
            st.subheader("🗺️ خريطة حالات الفاقد ذات الأولوية العالية")
            m = folium.Map(location=[high_priority_loss["Latitude"].mean(), high_priority_loss["Longitude"].mean()], zoom_start=10)
            for _, row in high_priority_loss.iterrows():
                folium.Marker(
                    location=[row["Latitude"], row["Longitude"]],
                    popup=f"عداد: {row['Meter Number']}\nالسبب: {row['Loss_Reason']}",
                    icon=folium.Icon(color="red")
                ).add_to(m)
            folium_static(m)
        
        # 🔹 **تحميل البيانات**
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            high_priority_loss.to_excel(writer, index=False)
        output.seek(0)
        st.download_button("📥 تحميل نتائج الفاقد ذات الأولوية العالية", data=output, file_name="high_priority_loss_cases.xlsx")

# 🏷️ **إضافة معلومات المطور**
st.markdown("---")
st.markdown("👨‍💻 **المطور: مشهور العباس-78598-00966553339838** | 📅 **تاريخ التحديث:** 08-03-2025")
