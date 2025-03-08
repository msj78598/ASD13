
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

# 🔹 **تحديث شروط تحديد الأولوية (High Priority)**
def set_priority(row):
    if (row['V1'] == 0 and row['A1'] > 0) or (row['V2'] == 0 and row['A2'] > 0) or (row['V3'] == 0 and row['A3'] > 0):
        return 'High'  # فاقد مؤكد
    elif (row['V1'] < 50 or row['V2'] < 50 or row['V3'] < 50) and (row['A1'] > 0 or row['A2'] > 0 or row['A3'] > 0):
        return 'High'  # فاقد محتمل
    elif (
        (row['V1'] == 0 and abs(row['A2'] - row['A3']) / max(row['A2'], row['A3']) > 0.6) or
        (row['V2'] == 0 and abs(row['A1'] - row['A3']) / max(row['A1'], row['A3']) > 0.6) or
        (row['V3'] == 0 and abs(row['A1'] - row['A2']) / max(row['A1'], row['A2']) > 0.6)
    ):
        return 'High'  # فاقد محتمل
    else:
        return 'Normal'

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
        data["Priority"] = data.apply(set_priority, axis=1)
        data["Loss_Reason"] = data.apply(add_loss_reason, axis=1)

        # 🔹 **إضافة الإحداثيات للعدادات ذات الفاقد**
        coords_df = load_coordinates()
        data = data.merge(coords_df, on="Meter Number", how="left")

        # 🔹 **عرض إحصائيات الفاقد**
        total_loss_cases = len(data[data["Predicted_Loss"] == 1])
        high_priority_cases = len(data[data["Priority"] == "High"])

        st.markdown("### 📊 ملخص النتائج")
        st.info(f"🔍 **عدد حالات الفاقد المكتشفة:** `{total_loss_cases}`")
        st.warning(f"🚨 **عدد حالات الفاقد ذات الأولوية العالية:** `{high_priority_cases}`")

        # 🔹 **عرض تحليل البيانات بيانياً**
        fig = px.scatter_matrix(
            data,
            dimensions=["V1", "V2", "V3", "A1", "A2", "A3"],
            color="Priority",
            title="📊 تحليل بيانات الفاقد المحتمل",
            color_discrete_map={"High": "red", "Normal": "blue"}
        )
        st.plotly_chart(fig)

        # 🔹 **عرض بيانات حالات الفاقد**
        loss_data = data[data["Predicted_Loss"] == 1]
        high_priority_loss = loss_data[loss_data["Priority"] == "High"]

        st.subheader("📋 جميع حالات الفاقد المكتشفة")
        st.dataframe(loss_data)

        st.subheader("🚨 حالات الفاقد ذات الأولوية العالية")
        st.dataframe(high_priority_loss)

        # 🔹 **إمكانية تحميل النتائج**
        output_loss = BytesIO()
        with pd.ExcelWriter(output_loss, engine='xlsxwriter') as writer:
            loss_data.to_excel(writer, index=False)
        output_loss.seek(0)
        st.download_button("📥 تحميل جميع حالات الفاقد", data=output_loss, file_name="all_loss_cases.xlsx")

        output_high_priority = BytesIO()
        with pd.ExcelWriter(output_high_priority, engine='xlsxwriter') as writer:
            high_priority_loss.to_excel(writer, index=False)
        output_high_priority.seek(0)
        st.download_button("🚨 تحميل حالات الفاقد ذات الأولوية العالية", data=output_high_priority, file_name="high_priority_loss_cases.xlsx")

        return high_priority_loss  # 🔹 **إرجاع حالات الفاقد ذات الأولوية العالية لاستخدامها في الخريطة**

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
high_priority_loss = None
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    high_priority_loss = analyze_data(df)

# 🌍 **عرض حالات الفاقد الأولية على الخريطة بعد التحليل**
if high_priority_loss is not None and not high_priority_loss.empty:
    if "Latitude" in high_priority_loss.columns and "Longitude" in high_priority_loss.columns:
        st.subheader("🗺️ خريطة حالات الفاقد ذات الأولوية العالية")
        
        m = folium.Map(location=[high_priority_loss["Latitude"].mean(), high_priority_loss["Longitude"].mean()], zoom_start=10, tiles="OpenStreetMap")

        for _, row in high_priority_loss.iterrows():
            popup_text = f"""
            <b>عداد:</b> {row["Meter Number"]}<br>
            <b>الجهد (V):</b> {row["V1"]}, {row["V2"]}, {row["V3"]}<br>
            <b>التيار (A):</b> {row["A1"]}, {row["A2"]}, {row["A3"]}<br>
            <b>السبب:</b> {row["Loss_Reason"]}
            """
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color="red")
            ).add_to(m)

        folium_static(m)
    else:
        st.warning("⚠️ لا توجد إحداثيات لحالات الفاقد الأولية في ملف الإحداثيات العام!")

# 🏷️ **إضافة معلومات المطور**
st.markdown("---")
st.markdown("👨‍💻 **المطور: مشهور العباس-78598-00966553339838** | 📅 **تاريخ التحديث:** 08-03-2025")
