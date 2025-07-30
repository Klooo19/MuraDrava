import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Postavljanje stranice
st.set_page_config(
    page_title="Excel File Reader",
    page_icon="📊",
    layout="wide"
)

# Naslov aplikacije
st.title("📊 Excel File Reader")
st.markdown("---")

# Funkcija za učitavanje datoteke
@st.cache_data
def load_file(file_path):
    """Učitava Excel ili CSV datoteku i vraća DataFrame"""
    try:
        # Provjeri ekstenziju datoteke
        if file_path.endswith('.csv'):
            # Pokušaj različite separatore za CSV
            separators = [',', ';', '\t', '|']
            df = None
            
            for sep in separators:
                try:
                    df_test = pd.read_csv(file_path, encoding='utf-8', sep=sep)
                    # Provjeri ima li više od jednog stupca (dobro parsiranje)
                    if len(df_test.columns) > 3:
                        df = df_test
                        st.info(f"✅ CSV uspješno učitan sa separatorom: '{sep}'")
                        break
                except:
                    continue
            
            # Ako nije uspjelo s UTF-8, pokušaj windows-1250
            if df is None:
                for sep in separators:
                    try:
                        df_test = pd.read_csv(file_path, encoding='windows-1250', sep=sep)
                        if len(df_test.columns) > 3:
                            df = df_test
                            st.info(f"✅ CSV uspješno učitan sa separatorom: '{sep}' i encoding: windows-1250")
                            break
                    except:
                        continue
            
            if df is None:
                return None, "Nije moguće parsirati CSV datoteku. Pokušajte s drugačijim formatom."
                
        elif file_path.endswith(('.xlsx', '.xls')):
            # Za Excel datoteke
            df = pd.read_excel(file_path)
        else:
            return None, f"Nepodržana ekstenzija datoteke: {file_path}"
        
        return df, None
    except FileNotFoundError:
        return None, f"Datoteka '{file_path}' nije pronađena."
    except Exception as e:
        return None, f"Greška pri učitavanju datoteke: {str(e)}"

# Funkcija za kreiranje grafova vodostaja
def create_water_level_charts(df):
    """Kreira grafove vodostaja za različite postaje"""
    
    st.subheader("📈 Grafički prikaz vodostaja")
    
    # Provjeri ima li CET/CEST stupac za datum/vrijeme
    datetime_col = None
    if 'CET/CEST' in df.columns:
        datetime_col = 'CET/CEST'
    elif any('datum' in col.lower() for col in df.columns):
        datetime_col = [col for col in df.columns if 'datum' in col.lower()][0]
    elif any('time' in col.lower() for col in df.columns):
        datetime_col = [col for col in df.columns if 'time' in col.lower()][0]
    
    if datetime_col is None:
        st.warning("⚠️ Nije pronađen stupac s datumom/vremenom za grafički prikaz.")
        return
    
    # Konvertiraj datum/vrijeme stupac
    try:
        df[datetime_col] = pd.to_datetime(df[datetime_col])
    except:
        st.error("❌ Greška pri konvertiranju datuma/vremena.")
        return
    
    # Pronađi sve stupce s vodostajem - poboljšana logika
    water_level_columns = []
    station_names = []
    
    # Debug: prikaži sve stupce
    st.write("**Debug - Svi stupci u datoteci:**")
    st.write(df.columns.tolist())
    
    # Poboljšana logika za prepoznavanje postaja
    station_mapping = {
        'MurskoSredisce': 'Mursko Središće',
        'Gorican': 'Goričan', 
        'DonjaDubrava': 'Donja Dubrava',
        'Gibina': 'Gibina',
        'KotoribaMost': 'Kotoriba Most',
        'SvMartinNaMuri': 'Sv. Martin na Muri',
        'VelikiPazut': 'Veliki Pazut'
    }
    
    for col in df.columns:
        # Preskoči CET/CEST, Botovo i Q stupce (protok)
        if col in [datetime_col, 'CET/CEST'] or col.startswith('Q.') or 'Botovo' in col:
            continue
            
        # Provjeri da li je stupac vodostaj (H vrijednosti)
        for station_key, station_display in station_mapping.items():
            if station_key in col:
                water_level_columns.append(col)
                station_names.append(station_display)
                break
    
    # Konvertiraj numeričke stupce
    for col in water_level_columns:
        try:
            # Pokušaj konvertirati u numerički tip
            df[col] = pd.to_numeric(df[col], errors='coerce')
        except:
            st.warning(f"⚠️ Problema s konverzijom stupca {col} u brojeve.")
    
    if not water_level_columns:
        st.warning("⚠️ Nisu pronađeni stupci s podacima o vodostaju.")
        return
    
    # Postavi filtere
    col1, col2 = st.columns(2)
    
    with col1:
        selected_stations = st.multiselect(
            "Odaberite postaje:",
            options=list(zip(station_names, water_level_columns)),
            default=[(station_names[0], water_level_columns[0])] if station_names else [],
            format_func=lambda x: x[0]  # Prikaži samo naziv postaje
        )
    
    with col2:
        chart_type = st.selectbox(
            "Tip grafa:",
            ["Linijski graf", "Površinski graf", "Scatter plot"]
        )
    
    if not selected_stations:
        st.info("ℹ️ Odaberite barem jednu postaju za prikaz grafa.")
        return
    
    # Filtriraj podatke samo za odabrane postaje
    selected_columns = [col for name, col in selected_stations]
    selected_names = [name for name, col in selected_stations]
    
    # Ukloni redove s NaN vrijednostima za vodostaj
    chart_data = df[[datetime_col] + selected_columns].dropna()
    
    if chart_data.empty:
        st.warning("⚠️ Nema podataka za prikaz grafa.")
        return
    
    # Kreiraj graf
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    
    for i, (station_name, col_name) in enumerate(selected_stations):
        if chart_type == "Linijski graf":
            fig.add_trace(go.Scatter(
                x=chart_data[datetime_col],
                y=chart_data[col_name],
                mode='lines+markers',
                name=station_name,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=4)
            ))
        elif chart_type == "Površinski graf":
            fig.add_trace(go.Scatter(
                x=chart_data[datetime_col],
                y=chart_data[col_name],
                mode='lines',
                name=station_name,
                fill='tonexty' if i > 0 else 'tozeroy',
                fillcolor=colors[i % len(colors)].replace('1.0', '0.3'),
                line=dict(color=colors[i % len(colors)])
            ))
        else:  # Scatter plot
            fig.add_trace(go.Scatter(
                x=chart_data[datetime_col],
                y=chart_data[col_name],
                mode='markers',
                name=station_name,
                marker=dict(color=colors[i % len(colors)], size=6)
            ))
    
    # Postavi layout grafa
    fig.update_layout(
        title=dict(
            text=f"Vodostaj - {', '.join(selected_names)}",
            x=0.5,
            font=dict(size=20)
        ),
        xaxis_title="Datum i vrijeme",
        yaxis_title="Vodostaj (cm)",
        hovermode='x unified',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    # Prikaži graf
    st.plotly_chart(fig, use_container_width=True)
    
    # Prikaži osnovne statistike za odabrane postaje
    if len(selected_stations) > 0:
        st.subheader("📊 Statistike vodostaja")
        
        stats_data = {}
        for station_name, col_name in selected_stations:
            data = chart_data[col_name].dropna()
            if not data.empty:
                stats_data[station_name] = {
                    'Min (cm)': data.min(),
                    'Max (cm)': data.max(),
                    'Prosjek (cm)': data.mean(),
                    'Medijan (cm)': data.median(),
                    'Std. devijacija': data.std()
                }
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data).T
            stats_df = stats_df.round(2)
            st.dataframe(stats_df, use_container_width=True)
    
    # Prikaži trenutne vrijednosti
    st.subheader("📍 Trenutne vrijednosti")
    current_values = {}
    
    for station_name, col_name in selected_stations:
        latest_value = chart_data[col_name].iloc[-1] if not chart_data[col_name].empty else None
        latest_time = chart_data[datetime_col].iloc[-1] if not chart_data.empty else None
        
        if latest_value is not None:
            current_values[station_name] = {
                'Vodostaj (cm)': latest_value,
                'Posljednje mjerenje': latest_time.strftime('%Y-%m-%d %H:%M:%S') if latest_time else 'N/A'
            }
    
    if current_values:
        current_df = pd.DataFrame(current_values).T
        st.dataframe(current_df, use_container_width=True)

# Glavna logika aplikacije
def main():
    # Naziv datoteke koju tražite
    target_filename = "2025-05-16_0700_redovni"
    
    st.subheader(f"Tražim datoteku: {target_filename}")
    
    # Pokušaj pronaći datoteku s različitim ekstenzijama
    possible_extensions = ['.xlsx', '.xls', '.csv']
    found_file = None
    
    for ext in possible_extensions:
        file_path = target_filename + ext
        if os.path.exists(file_path):
            found_file = file_path
            break
    
    if found_file:
        st.success(f"✅ Datoteka pronađena: {found_file}")
        
        # Učitaj datoteku
        with st.spinner("Učitavam datoteku..."):
            df, error = load_file(found_file)
        
        if df is not None:
            st.success("🎉 Datoteka uspješno učitana!")
            
            # Prikaži osnovne informacije o datoteci
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Broj redaka", len(df))
            with col2:
                st.metric("Broj stupaca", len(df.columns))
            with col3:
                st.metric("Veličina (MB)", f"{df.memory_usage(deep=True).sum() / 1024**2:.2f}")
            
            # Prikaži strukturu podataka
            st.subheader("📋 Struktura podataka")
            st.write("**Nazivi stupaca:**")
            st.write(list(df.columns))
            
            # Prikaži prve redove
            st.subheader("👀 Pregled podataka (prvih 10 redaka)")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Osnovne statistike za numeričke stupce
            numeric_columns = df.select_dtypes(include=['number']).columns
            if len(numeric_columns) > 0:
                st.subheader("📊 Osnovne statistike")
                st.dataframe(df[numeric_columns].describe(), use_container_width=True)
            
            # Opcija za preuzimanje obrađenih podataka
            st.subheader("💾 Preuzmi podatke")
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Preuzmi kao CSV",
                data=csv,
                file_name=f"{target_filename}_processed.csv",
                mime="text/csv"
            )
            
            # Dodaj vizualizacije ako postoje vodostaj podaci
            create_water_level_charts(df)
            
        else:
            st.error(f"❌ {error}")
    
    else:
        st.warning(f"⚠️ Datoteka '{target_filename}' nije pronađena u trenutnom direktoriju.")
        
        # Prikaz dostupnih datoteka
        st.subheader("📁 Dostupne datoteke u direktoriju:")
        files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls', '.csv'))]
        
        if files:
            for file in files:
                st.write(f"• {file}")
        else:
            st.write("Nema Excel/CSV datoteka u trenutnom direktoriju.")
        
        # Upload opcija
        st.subheader("📤 Ili uploadajte datoteku:")
        uploaded_file = st.file_uploader(
            "Odaberite Excel datoteku",
            type=['xlsx', 'xls', 'csv'],
            help="Podržani formati: .xlsx, .xls, .csv"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.success("🎉 Datoteka uspješno uploadana i učitana!")
                
                # Prikaži podatke kao i prije
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Broj redaka", len(df))
                with col2:
                    st.metric("Broj stupaca", len(df.columns))
                with col3:
                    st.metric("Veličina (MB)", f"{df.memory_usage(deep=True).sum() / 1024**2:.2f}")
                
                st.subheader("👀 Pregled podataka")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Dodaj vizualizacije
                create_water_level_charts(df)
                
            except Exception as e:
                st.error(f"❌ Greška pri učitavanju datoteke: {str(e)}")

# Pokretanje aplikacije
if __name__ == "__main__":
    main()

# Sidebar s informacijama
st.sidebar.markdown("### ℹ️ Informacije")
st.sidebar.markdown("""
**Kako koristiti:**
1. Stavite CSV/Excel datoteku u isti direktorij kao ovu skriptu
2. Datoteka mora imati naziv: `2025-05-16_0700_redovni`
3. Podržane ekstenzije: `.xlsx`, `.xls`, `.csv`
4. Ili koristite upload opciju

**Funkcionalnosti:**
- Automatsko pronalaženje datoteke
- Pregled strukture podataka
- Osnovne statistike
- Export u CSV format
- 📈 Grafički prikaz vodostaja
- 📊 Statistike za odabrane postaje
- 📍 Trenutne vrijednosti vodostaja
""")

st.sidebar.markdown("---")
st.sidebar.markdown("📧 Za pomoć kontaktirajte razvojni tim")