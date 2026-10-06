import pandas as pd
import streamlit as st

st.set_page_config(page_title="Калькулятор отгрузки", layout="wide")

# Инициализация состояния "корзины"
if 'cart' not in st.session_state:
    st.session_state.cart = pd.DataFrame(columns=["Код", "Мешков", "Штук", "Объем_чистый", "Объем_плюс_10", "Вес"])

@st.cache_data
def load_data():
    return pd.read_excel("Расчет объема.xlsx")

try:
    df = load_data()
    catalog = {}
    for index, row in df.iterrows():
        code = str(row.get('Код', '')).strip()
        if code and code != 'nan':
            catalog[code] = {
                'вес_1_шт': pd.to_numeric(row.get('Вес 1 шт, кг', 0), errors='coerce'),
                'шт_в_мешке': pd.to_numeric(row.get('Кол-во шт мешке', 0), errors='coerce'),
                'объем_мешка': pd.to_numeric(row.get('Объем мешка, м.куб', 0), errors='coerce')
            }
except Exception as e:
    st.error("Ошибка загрузки базы данных. Проверьте файл Расчет объема.xlsx")
    st.stop()

st.title("📦 Сводный калькулятор отгрузки")

# --- Блок выбора товаров ---
st.subheader("1. Выбор позиций")
selected_codes = st.multiselect("Выберите коды товаров (можно несколько):", list(catalog.keys()))

# --- Блок ввода количества и добавления ---
if selected_codes:
    st.write("**2. Укажите количество мешков для каждой позиции:**")
    
    # Используем форму (st.form), чтобы не обновлять страницу при каждом вводе цифры
    with st.form("add_to_cart_form"):
        bags_inputs = {}
        
        # Динамически создаем строчку с вводом количества для каждого выбранного кода
        for code in selected_codes:
            col_name, col_input = st.columns([1, 3])
            with col_name:
                st.markdown(f"<h5 style='margin-top: 5px;'>{code}</h5>", unsafe_allow_html=True)
            with col_input:
                bags_inputs[code] = st.number_input(f"Мешков для {code}", min_value=1.0, value=1.0, step=1.0, label_visibility="collapsed", key=f"bag_{code}")
        
        # Кнопка отправки формы
        submitted = st.form_submit_button("➕ Добавить в расчет")
        
        if submitted:
            for code in selected_codes:
                bags_count = bags_inputs[code]
                item = catalog[code]
                
                # Математика
                total_pieces = bags_count * item['шт_в_мешке']
                net_volume = bags_count * item['объем_мешка']
                volume_plus_10 = net_volume * 1.10
                total_weight = total_pieces * item['вес_1_шт']
                
                # Проверка, есть ли код в таблице
                existing_idx = st.session_state.cart.index[st.session_state.cart['Код'] == code].tolist()
                
                if existing_idx:
                    # Если есть - прибавляем к существующим
                    idx = existing_idx[0]
                    new_bags = st.session_state.cart.at[idx, 'Мешков'] + bags_count
                    
                    st.session_state.cart.at[idx, 'Мешков'] = new_bags
                    st.session_state.cart.at[idx, 'Штук'] = new_bags * item['шт_в_мешке']
                    st.session_state.cart.at[idx, 'Объем_чистый'] = new_bags * item['объем_мешка']
                    st.session_state.cart.at[idx, 'Объем_плюс_10'] = (new_bags * item['объем_мешка']) * 1.10
                    st.session_state.cart.at[idx, 'Вес'] = (new_bags * item['шт_в_мешке']) * item['вес_1_шт']
                else:
                    # Если нет - создаем новую строку
                    new_row = pd.DataFrame([{
                        "Код": code,
                        "Мешков": bags_count,
                        "Штук": total_pieces,
                        "Объем_чистый": net_volume,
                        "Объем_плюс_10": volume_plus_10,
                        "Вес": total_weight
                    }])
                    st.session_state.cart = pd.concat([st.session_state.cart, new_row], ignore_index=True)
            st.rerun() # Обновляем страницу для вывода таблицы

# --- Блок таблицы и итогов ---
st.divider()

if not st.session_state.cart.empty:
    col_table, col_clear = st.columns([8, 1])
    with col_table:
        st.subheader("📊 Текущий заказ")
    with col_clear:
        if st.button("🗑️ Очистить", use_container_width=True):
            st.session_state.cart = pd.DataFrame(columns=["Код", "Мешков", "Штук", "Объем_чистый", "Объем_плюс_10", "Вес"])
            st.rerun()

    # Форматирование таблицы
    display_df = st.session_state.cart.copy()
    display_df['Штук'] = display_df['Штук'].map('{:g}'.format)
    display_df['Объем_чистый'] = display_df['Объем_чистый'].map('{:.3f}'.format)
    display_df['Объем_плюс_10'] = display_df['Объем_плюс_10'].map('{:.3f}'.format)
    display_df['Вес'] = display_df['Вес'].map('{:.2f}'.format)
    display_df.rename(columns={'Объем_чистый': 'Объем (чистый)', 'Объем_плюс_10': 'Объем (+10%)'}, inplace=True)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Итоги
    total_bags = st.session_state.cart['Мешков'].sum()
    total_pcs = st.session_state.cart['Штук'].sum()
    total_vol = st.session_state.cart['Объем_чистый'].sum()
    total_vol10 = st.session_state.cart['Объем_плюс_10'].sum()
    total_weight = st.session_state.cart['Вес'].sum()

    st.success("Итоги по заказу:")
    res_col1, res_col2, res_col3, res_col4, res_col5 = st.columns(5)
    res_col1.metric("Всего мешков", f"{total_bags:g}")
    res_col2.metric("Всего штук", f"{total_pcs:g}")
    res_col3.metric("Общий объем", f"{total_vol:.3f} м³")
    res_col4.metric("Объем +10%", f"{total_vol10:.3f} м³")
    res_col5.metric("Общий вес", f"{total_weight:.2f} кг")

else:
    st.info("Таблица расчетов пуста. Выберите товары, укажите количество и нажмите 'Добавить в расчет'.")
