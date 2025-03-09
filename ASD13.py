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
        return 'High'
    elif (row['V1'] < 50 or row['V2'] < 50 or row['V3'] < 50) and (row['A1'] > 0 or row['A2'] > 0 or row['A3'] > 0):
        return 'High'
    elif (
        (row['V1'] == 0 and max(row['A2'], row['A3']) > 0 and abs(row['A2'] - row['A3']) / max(row['A2'], row['A3']) > 0.6) or
        (row['V2'] == 0 and max(row['A1'], row['A3']) > 0 and abs(row['A1'] - row['A3']) / max(row['A1'], row['A3']) > 0.6) or
        (row['V3'] == 0 and max(row['A1'], row['A2']) > 0 and abs(row['A1'] - row['A2']) / max(row['A1'], row['A2']) > 0.6)
    ):
        return 'High'
    else:
        return 'Normal'

# 🔹 **إضافة تفسير واضح لحالات الفاقد**
def add_loss_reason(row):
    if (row['V1'] == 0 and row['A1'] > 0):
        return '⚠️ فقد مؤكد (الجهد V1=0 مع تيار)'
    elif (row['V2'] == 0 and row['A2'] > 0):
        return '⚠️ فقد بسبب جهد صفر وتيار على V2'
    elif (row['V3'] == 0 and row['A3'] > 0):
        return '⚠️ فقد بسبب جهد صفر وتيار على V3'
    elif (row['V1'] < 50 or row['V2'] < 50 or row['V3'] < 50) and (row['A1'] > 0 or row['A2'] > 0 or row['A3'] > 0):
        return '⚠️ فقد محتمل بسبب انخفاض شديد في الجهد مع وجود تيار'
    elif (
        (row['V1'] == 0 and max(row['A2'], row['A3']) > 0 and abs(row['A2'] - row['A3']) / max(row['A2'], row['A3']) > 0.6) or
        (row['V2'] == 0 and max(row['A1'], row['A3']) > 0 and abs(row['A1'] - row['A3']) / max(row['A1'], row['A3']) > 0.6) or
        (row['V3'] == 0 and max(row['A1'], row['A2']) > 0 and abs(row['A1'] - row['A2']) / max(row['A1'], row['A2']) > 0.6)
    ):
        return '⚠️ فقد محتمل بسبب فرق التيار الكبير بين فازتين مع انعدام الجهد في الثالثة'
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

        X = data[required_columns[1:]]
        predictions = model.predict(X)
        data["Predicted_Loss"] = predictions
        data["Priority"] = data.apply(set_priority, axis=1)
        data["Loss_Reason"] = data.apply(add_loss_reason, axis=1)

        coords_df = load_coordinates()
        data = data.merge(coords_df, on="Meter Number", how="left")

        loss_data = data[data["Predicted_Loss"] == 1]
        high_priority_loss = loss_data[loss_data["Priority"] == "High"]

        st.subheader("📋 جميع حالات الفاقد المكتشفة")
        st.dataframe(loss_data)

        st.subheader("🚨 حالات الفاقد ذات الأولوية العالية")
        st.dataframe(high_priority_loss)

        # تحميل النتائج
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

        return high_priority_loss

    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء تحليل البيانات: {str(e)}")
        return None

# 📥 **رفع ملف البيانات للتحليل**
st.subheader("📊 نظام اكتشاف حالات الفاقد المحتملة")
uploaded_file = st.file_uploader("📤 قم برفع ملف البيانات للتحليل (Excel)", type=["xlsx"])
high_priority_loss = None
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    high_priority_loss = analyze_data(df)

# 🏷️ **إضافة معلومات المطور**
st.markdown("---")
st.markdown("👨‍💻 **المطور: مشهور العباس-78598-00966553339838** | 📅 **تاريخ التحديث:** 08-03-2025")
```

هذا هو الكود الكامل بصيغة واضحة مع **تصحيح جميع الأخطاء** السابقة وجاهز للاستخدام مباشرة في Streamlit.
