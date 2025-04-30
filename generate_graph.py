import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from collections import defaultdict

# --- Configuration ---
DB_FILE = 'pokemon_data.db'
OUTPUT_HTML = 'pokemon_analysis_report_v2.html'
GENERATIONS = range(1, 10) # Generations 1 through 9
STATS_COLUMNS = ['hp', 'attack', 'defense', 'special_attack', 'special_defense', 'speed']
STAT_NAMES_FULL = ['HP', 'Attack', 'Defense', 'Special Attack', 'Special Defense', 'Speed'] # For Radar chart

# --- Helper Functions ---

def create_html_report(plots_html, tables_html, title="Pokémon Data Analysis Report"):
    """Generates the final HTML file content."""
    plotly_js = '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'
    css_style = """
<style>
    body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
    h1 { text-align: center; color: #e4000f; /* Pokemon Red */ }
    h2 { color: #3b4cca; /* Pokemon Blue */ border-bottom: 2px solid #ffde00; /* Pokemon Yellow */ padding-bottom: 5px; margin-top: 40px; }
    .plot-container, .table-container {
        margin-bottom: 30px;
        padding: 20px;
        border: 1px solid #ccc;
        border-radius: 8px;
        background-color: #fff;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
        gap: 20px;
        margin-top: 15px;
    }
    .grid-item { /* Style individual grid items if needed */ }
    table { border-collapse: collapse; width: 100%; margin-top: 15px; }
    th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
    th { background-color: #f2f2f2; font-weight: bold; }
    tr:nth-child(even) { background-color: #f9f9f9; }
    tr:hover { background-color: #eef; }
</style>
"""

    body_content = f"<h1>{title}</h1>"

    # Group plots logically if desired, or just list them
    plot_order = [
        "Type Count per Generation (Absolute)",
        "Type Percentage per Generation (%)",
        "Average BST of Fully Evolved Pokémon by Type",
        "Average BST of Fully Evolved Pokémon Over Generations",
        "Average Stats (Fully Evolved) Radar per Generation", # New Radar Chart
        "Average Stats (Fully Evolved) Histograms per Generation", # New Histograms
        "Distribution of Pokémon Stages per Generation (%)",
        "Approximate Average BST Gain During Evolution",
        "BST vs. Stat Spread",
        "Pie Charts: Type Distribution per Generation" # Keep pies maybe lower down or handle grid separately
    ]

    for key in plot_order:
        if key in plots_html:
            html_content = plots_html[key]
            if key == "Pie Charts: Type Distribution per Generation":
                # Special handling for pie chart grid
                pie_html_list = html_content # It's already a list
                if pie_html_list: # Check if list is not empty
                    pie_grid_content = "<div class='grid-container'>\n"
                    for gen_pie_html in pie_html_list:
                        pie_grid_content += f"<div class='grid-item'>{gen_pie_html}</div>\n"
                    pie_grid_content += "</div>"
                    body_content += f"<div class='plot-container'>\n<h2>{key}</h2>\n{pie_grid_content}\n</div>\n"
            else:
                # Standard plot container
                body_content += f"<div class='plot-container'>\n<h2>{key}</h2>\n{html_content}\n</div>\n"

    # Add tables
    table_keys_sorted = sorted(tables_html.keys(), key=lambda x: int(x.split(' ')[1].replace(':', ''))) # Sort Gen 1, Gen 2...
    if table_keys_sorted:
        body_content += f"<div class='table-container'>\n<h2>Stat Leaders per Generation</h2>\n"
        body_content += "<div class='grid-container'>\n" # Use grid for tables too
        for key in table_keys_sorted:
            html_content = tables_html[key]
            # Put each table in its own sub-container within the grid
            body_content += f"<div class='grid-item'><h3>{key}</h3>{html_content}</div>\n"
        body_content += "</div>\n</div>\n" # Close grid and table-container

    full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    {plotly_js}
    {css_style}
</head>
<body>
{body_content}
</body>
</html>
    """
    return full_html

def get_all_types(df):
    """Gets a sorted list of all unique Pokémon types."""
    types1 = df['type1'].unique()
    types2 = df['type2'].dropna().unique()
    all_types = set(types1) | set(types2)
    all_types = {t for t in all_types if t and pd.notna(t)} # Remove empty/None
    return sorted(list(all_types))

def load_and_prepare_data(db_path):
    """Loads data from SQLite DB and performs initial cleaning."""
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.")
        return None

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM pokemon", conn)
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")
        return None

    print(f"Loaded {len(df)} Pokémon records.")

    # Data Cleaning / Preparation
    df['type2'] = df['type2'].fillna('')
    df['is_fully_evolved'] = df['is_fully_evolved'].astype(bool)
    
    numeric_cols = ['hp', 'attack', 'defense', 'special_attack', 'special_defense', 'speed', 'bst', 'stage', 'generation', 'id']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    original_count = len(df)
    df.dropna(subset=numeric_cols, inplace=True) # Drop rows if essential numbers are missing
    if len(df) < original_count:
        print(f"Warning: Dropped {original_count - len(df)} rows with missing numeric data.")

    # Add stat std dev column needed later
    df['stat_std_dev'] = df[STATS_COLUMNS].std(axis=1)

    return df

# --- Plotting Functions ---

def plot_type_count_absolute(df, all_types, generations):
    """Generates Line Chart: Type Count per Generation (Absolute)."""
    print("Plotting: Type Count per Generation (Absolute)...")
    type_counts_per_gen = defaultdict(lambda: defaultdict(int))
    for gen in generations:
        df_gen = df[df['generation'] == gen]
        for type_name in all_types:
            count1 = df_gen[df_gen['type1'] == type_name].shape[0]
            count2 = df_gen[df_gen['type2'] == type_name].shape[0]
            type_counts_per_gen[gen][type_name] = count1 + count2 # Count occurrences in either slot

    type_trend_df = pd.DataFrame(type_counts_per_gen).fillna(0).astype(int)
    type_trend_df = type_trend_df.reindex(all_types, fill_value=0).sort_index()

    fig = px.line(
        type_trend_df.T, # Transpose for generations on x-axis
        labels={'index': 'Generation', 'value': 'Number of Pokémon Appearances', 'variable': 'Type'},
        markers=True
    )
    fig.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    return fig.to_html(full_html=False, include_plotlyjs=False)

def plot_type_count_percentage(df, all_types, generations):
    """Generates Line Chart: Type Percentage per Generation (%)."""
    print("Plotting: Type Percentage per Generation (%)...")
    type_counts_per_gen = defaultdict(lambda: defaultdict(int))
    total_type_slots_per_gen = defaultdict(int)

    for gen in generations:
        df_gen = df[df['generation'] == gen]
        gen_total_slots = 0
        for _, row in df_gen.iterrows():
            type_counts_per_gen[gen][row['type1']] += 1
            gen_total_slots += 1
            if row['type2']:
                type_counts_per_gen[gen][row['type2']] += 1
                gen_total_slots += 1
        total_type_slots_per_gen[gen] = gen_total_slots


    type_perc_df = pd.DataFrame(type_counts_per_gen).fillna(0)
    
    # Divide count of each type by total type slots in that generation
    for gen in generations:
        if total_type_slots_per_gen[gen] > 0:
             type_perc_df[gen] = (type_perc_df[gen] / total_type_slots_per_gen[gen]) * 100
        else:
            type_perc_df[gen] = 0 # Avoid division by zero if a gen has no pokemon

    type_perc_df = type_perc_df.reindex(all_types, fill_value=0).sort_index()

    fig = px.line(
        type_perc_df.T, # Transpose
        labels={'index': 'Generation', 'value': 'Percentage of Type Slots (%)', 'variable': 'Type'},
        markers=True
    )
    fig.update_layout(yaxis_ticksuffix="%", xaxis=dict(tickmode='linear', dtick=1))
    return fig.to_html(full_html=False, include_plotlyjs=False)


def plot_avg_bst_fe_by_type(df, all_types):
    """Generates Bar Chart: Average BST of Fully Evolved Pokémon by Type."""
    print("Plotting: Average BST of Fully Evolved by Type...")
    df_fully_evolved = df[df['is_fully_evolved']].copy()
    if df_fully_evolved.empty:
        print("Warning: No fully evolved Pokémon found.")
        return "<div>No fully evolved Pokémon data available for BST analysis by type.</div>"

    bst_by_type = defaultdict(list)
    for _, row in df_fully_evolved.iterrows():
        bst_by_type[row['type1']].append(row['bst'])
        if row['type2']:
            bst_by_type[row['type2']].append(row['bst'])

    avg_bst_type = {type_name: np.mean(bst_list)
                    for type_name, bst_list in bst_by_type.items() if bst_list and type_name in all_types} # Ensure type is valid
    
    if not avg_bst_type:
        return "<div>Could not calculate average BST per type for fully evolved Pokémon.</div>"

    avg_bst_type_df = pd.DataFrame(list(avg_bst_type.items()), columns=['Type', 'Average BST']).sort_values('Average BST', ascending=False)

    fig = px.bar(
        avg_bst_type_df,
        x='Type',
        y='Average BST',
        labels={'Average BST': 'Average Base Stat Total'}
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)

def plot_avg_bst_fe_over_gens(df, generations):
    """Generates Line Chart: Average BST of Fully Evolved Pokémon Over Generations."""
    print("Plotting: Average BST of Fully Evolved over Generations...")
    df_fully_evolved = df[df['is_fully_evolved']].copy()
    if df_fully_evolved.empty:
        print("Warning: No fully evolved Pokémon found.")
        return "<div>No fully evolved Pokémon data available for BST trend analysis.</div>"

    avg_bst_gen = df_fully_evolved.groupby('generation')['bst'].mean().reset_index()
    # Ensure all generations are present, potentially with NaN if no FE pokemon exist
    avg_bst_gen = avg_bst_gen.set_index('generation').reindex(generations).reset_index()


    fig = px.line(
        avg_bst_gen,
        x='generation',
        y='bst',
        labels={'generation': 'Generation', 'bst': 'Average Base Stat Total'},
        markers=True
    )
    fig.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    return fig.to_html(full_html=False, include_plotlyjs=False)

def plot_avg_stats_fe_radar_per_gen(df, generations):
    """Generates separate Radar Charts: Average Stats of Fully Evolved Pokémon per Generation."""
    print("Plotting: Average Stats Radar per Generation...")
    df_fully_evolved = df[df['is_fully_evolved']].copy()
    if df_fully_evolved.empty:
        print("Warning: No fully evolved Pokémon found.")
        return ["<div>No fully evolved Pokémon data available for radar chart analysis.</div>"]

    avg_stats_gen = df_fully_evolved.groupby('generation')[STATS_COLUMNS].mean()
    # Ensure all generations are potentially present
    avg_stats_gen = avg_stats_gen.reindex(generations)  # Will have NaN rows if a gen has no FE Pokémon

    radar_charts = []
    theta_labels = STAT_NAMES_FULL + [STAT_NAMES_FULL[0]]  # Repeat first stat to close loop

    for gen in generations:
        if gen in avg_stats_gen.index and not avg_stats_gen.loc[gen].isnull().all():
            stats_values = avg_stats_gen.loc[gen].tolist()
            stats_values_closed = stats_values + [stats_values[0]]  # Close the loop

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=stats_values_closed,
                theta=theta_labels,
                fill='toself',
                name=f'Generation {gen}'
            ))

            fig.update_layout(
                title=f"Average Stats Radar Chart - Generation {gen}",
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, df_fully_evolved[STATS_COLUMNS].max().max() * 1.1]  # Set range based on max observed stat + 10%
                    )
                ),
                showlegend=False
            )

            radar_charts.append(fig.to_html(full_html=False, include_plotlyjs=False))
        else:
            print(f"Note: No fully evolved Pokémon data for Generation {gen}, skipping radar chart.")
            radar_charts.append(f"<div>No data available for Generation {gen}.</div>")

    return radar_charts

def plot_avg_stats_fe_histograms_per_gen(df, generations):
    """Generates separate Histograms: Average Stats of Fully Evolved Pokémon per Generation."""
    print("Plotting: Average Stats Histograms per Generation...")
    df_fully_evolved = df[df['is_fully_evolved']].copy()
    if df_fully_evolved.empty:
        print("Warning: No fully evolved Pokémon found.")
        return ["<div>No fully evolved Pokémon data available for histogram analysis.</div>"]

    avg_stats_gen = df_fully_evolved.groupby('generation')[STATS_COLUMNS].mean()
    # Ensure all generations are potentially present
    avg_stats_gen = avg_stats_gen.reindex(generations)  # Will have NaN rows if a gen has no FE Pokémon

    histograms = []

    for gen in generations:
        if gen in avg_stats_gen.index and not avg_stats_gen.loc[gen].isnull().all():
            stats_values = avg_stats_gen.loc[gen]

            fig = px.bar(
                x=STAT_NAMES_FULL,
                y=stats_values,
                labels={'x': 'Stat', 'y': 'Average Value'},
                title=f"Average Stats Histogram - Generation {gen}"
            )
            fig.update_traces(
                hovertemplate="Stat: %{x}<br>Average Value: %{y}<extra></extra>"
            )
            fig.update_layout(
                xaxis_title="Stat",
                yaxis_title="Average Value",
                yaxis=dict(range=[0, df_fully_evolved[STATS_COLUMNS].max().max() * 1.1])  # Set range based on max observed stat + 10%
            )

            histograms.append(fig.to_html(full_html=False, include_plotlyjs=False))
        else:
            print(f"Note: No fully evolved Pokémon data for Generation {gen}, skipping histogram.")
            histograms.append(f"<div>No data available for Generation {gen}.</div>")

    return histograms

def generate_stat_leader_tables(df, generations):
    """Generates Tables: Stat Leaders per Generation."""
    print("Generating: Stat Leader Tables...")
    tables_html = {}
    stat_names_map = {
        'hp': 'Highest HP', 'attack': 'Highest Attack', 'defense': 'Highest Defense',
        'special_attack': 'Highest Sp. Attack', 'special_defense': 'Highest Sp. Defense',
        'speed': 'Highest Speed', 'bst': 'Highest BST'
    }
    stats_for_table = STATS_COLUMNS + ['bst'] # Use list defined earlier + bst

    for gen in generations:
        df_gen = df[df['generation'] == gen].copy()
        if df_gen.empty:
            tables_html[f"Generation {gen}: Stat Leaders"] = "<p>No Pokémon data for this generation.</p>"
            continue

        leaders = []
        for stat in stats_for_table:
            if stat not in df_gen.columns or df_gen[stat].isnull().all():
                leaders.append({
                    'Stat': stat_names_map.get(stat, stat.upper()),
                    'Value': 'N/A',
                    'Pokémon': 'N/A'
                })
                continue
                
            try:
                # Handle potential ties by taking the first one found by idxmax
                idx_max = df_gen[stat].idxmax() 
                pokemon_leader = df_gen.loc[idx_max]
                leaders.append({
                    'Stat': stat_names_map.get(stat, stat.upper()),
                    'Value': pokemon_leader[stat],
                    'Pokémon': pokemon_leader['name']
                })
            except ValueError: # idxmax raises ValueError if all values are NaN
                leaders.append({
                    'Stat': stat_names_map.get(stat, stat.upper()),
                    'Value': 'N/A',
                    'Pokémon': 'N/A'
                })


        leaders_df = pd.DataFrame(leaders)
        # Use border=0 because CSS adds borders
        tables_html[f"Generation {gen}: Stat Leaders"] = leaders_df.to_html(index=False, classes='stat-leader-table', border=0, na_rep='N/A')

    return tables_html # Return dict of HTML strings


def plot_stage_distribution(df, generations):
    """Generates Bar Chart: Evolution Stage Distribution per Generation."""
    print("Plotting: Evolution Stage Distribution...")
    # Count Pokémon records per stage per generation
    stage_counts = df.groupby(['generation', 'stage']).size().unstack(fill_value=0)
    
    # Check if stage column exists and has data
    if stage_counts.empty:
        return "<div>No stage data available for distribution analysis.</div>"
        
    # Ensure all expected stages (e.g., 1, 2, 3) are columns, fill missing with 0
    expected_stages = sorted(df['stage'].unique())
    stage_counts = stage_counts.reindex(columns=expected_stages, fill_value=0)

    # Calculate percentage
    stage_perc = stage_counts.apply(lambda x: x / x.sum() * 100 if x.sum() > 0 else 0, axis=1)
    
    stage_perc = stage_perc.reindex(generations).reset_index() # Ensure all gens are present
    stage_perc_melt = stage_perc.melt(id_vars='generation', var_name='Stage', value_name='Percentage')
    # Convert Stage back to string/category for better labeling if needed
    stage_perc_melt['Stage'] = stage_perc_melt['Stage'].astype(str)

    fig = px.bar(
        stage_perc_melt,
        x='generation',
        y='Percentage',
        color='Stage',
        barmode='group',
        labels={'generation': 'Generation', 'Percentage': '% of Pokémon in Gen', 'Stage': 'Evolution Stage'},
        category_orders={"Stage": sorted(stage_perc_melt['Stage'].unique())} # Ensure stages are ordered
    )
    fig.update_layout(yaxis_ticksuffix="%", xaxis=dict(tickmode='linear', dtick=1))
    return fig.to_html(full_html=False, include_plotlyjs=False)

def plot_avg_bst_gain(df, generations):
    """Generates Bar Chart: Approximate Average BST Increase During Evolution."""
    print("Plotting: Average BST Increase (Approximation)...")
    # Calculate average BST per stage per generation
    avg_bst_stage_gen = df.groupby(['generation', 'stage'])['bst'].mean().unstack()

    # Check if sufficient stage data exists
    if avg_bst_stage_gen.empty or len(avg_bst_stage_gen.columns) < 2:
        return "<div>Insufficient stage data to calculate BST gain. Needs at least two stages per generation.</div>"

    # Calculate approximate gain: Stage 2 avg - Stage 1 avg, Stage 3 avg - Stage 2 avg
    # Use .get(col, default=pd.NA) to handle missing stages gracefully
    avg_bst_stage_gen['Gain S1->S2'] = avg_bst_stage_gen.get(2, pd.NA) - avg_bst_stage_gen.get(1, pd.NA)
    if 3 in avg_bst_stage_gen.columns and 2 in avg_bst_stage_gen.columns:
        avg_bst_stage_gen['Gain S2->S3'] = avg_bst_stage_gen.get(3, pd.NA) - avg_bst_stage_gen.get(2, pd.NA)
    else:
        avg_bst_stage_gen['Gain S2->S3'] = pd.NA


    # Calculate average gain per generation (averaging the non-NA gains)
    gain_cols = [col for col in ['Gain S1->S2', 'Gain S2->S3'] if col in avg_bst_stage_gen.columns]
    if not gain_cols:
        return "<div>Could not calculate any BST gains between stages.</div>"
        
    avg_bst_stage_gen['Avg Gain'] = avg_bst_stage_gen[gain_cols].mean(axis=1, skipna=True)

    avg_gain_df = avg_bst_stage_gen.reset_index()[['generation', 'Avg Gain']].dropna()
    # Ensure all generations are represented, potentially with NaN
    avg_gain_df = avg_gain_df.set_index('generation').reindex(generations).reset_index()


    fig = px.bar(
        avg_gain_df,
        x='generation',
        y='Avg Gain',
        labels={'generation': 'Generation', 'Avg Gain': 'Average BST Increase'},
    )
    fig.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    return fig.to_html(full_html=False, include_plotlyjs=False)

def plot_bst_vs_stat_stddev(df):
    """Generates Scatterplot: BST vs. Stat Standard Deviation."""
    print("Plotting: BST vs Stat Spread...")
    
    # Ensure the 'stat_std_dev' column exists (should be added in load_and_prepare_data)
    if 'stat_std_dev' not in df.columns or 'bst' not in df.columns:
        return "<div>Required columns 'bst' or 'stat_std_dev' missing for scatter plot.</div>"

    fig = px.scatter(
        df.dropna(subset=['bst', 'stat_std_dev']), # Drop rows where these specific values are NaN
        x='bst',
        y='stat_std_dev',
        hover_data=['name', 'generation', 'type1', 'type2'],
        labels={'bst': 'Base Stat Total (BST)', 'stat_std_dev': 'Standard Deviation of Base Stats'},
        trendline='ols', # Add Ordinary Least Squares trendline
        trendline_color_override="red"
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


# --- Main Analysis Function ---
def run_analysis():
    """Loads data, runs all analyses, and returns HTML components."""

    df = load_and_prepare_data(DB_FILE)
    if df is None:
        return None, None

    all_types = get_all_types(df)
    plots_html = {}
    tables_html = {} # Changed from list to dict

    # Call each plotting function
    try:
        plots_html["Type Count per Generation (Absolute)"] = plot_type_count_absolute(df, all_types, GENERATIONS)
        plots_html["Type Percentage per Generation (%)"] = plot_type_count_percentage(df, all_types, GENERATIONS)
        plots_html["Average BST of Fully Evolved Pokémon by Type"] = plot_avg_bst_fe_by_type(df, all_types)
        plots_html["Average BST of Fully Evolved Pokémon Over Generations"] = plot_avg_bst_fe_over_gens(df, GENERATIONS)
        #plots_html["Average Stats (Fully Evolved) Radar per Generation"] = plot_avg_stats_fe_radar_per_gen(df, GENERATIONS) # New Radar
        plots_html["Average Stats (Fully Evolved) Histograms per Generation"] = plot_avg_stats_fe_histograms_per_gen(df, GENERATIONS) # New Histograms
        plots_html["Distribution of Pokémon Stages per Generation (%)"] = plot_stage_distribution(df, GENERATIONS)
        plots_html["Approximate Average BST Gain During Evolution"] = plot_avg_bst_gain(df, GENERATIONS)
        plots_html["BST vs. Stat Spread"] = plot_bst_vs_stat_stddev(df)

        # Call table generation function
        tables_html = generate_stat_leader_tables(df, GENERATIONS) # Returns dict

    except Exception as e:
        print(f"\n--- An error occurred during analysis ---")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        print("--- Continuing report generation with available plots/tables ---")
        # Return whatever was generated so far
        
    print("\nAnalysis generation complete.")
    return plots_html, tables_html


# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Pokémon Data Analysis...")
    plots, tables = run_analysis()

    if plots is not None and tables is not None:
        print(f"Generating HTML report: {OUTPUT_HTML}...")
        report_html = create_html_report(plots, tables, title="Pokémon Generations Data Analysis")

        try:
            with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
                f.write(report_html)
            print(f"\nSuccessfully created report: {OUTPUT_HTML}")
            # Try to open the report automatically (optional)
            try:
                import webbrowser
                webbrowser.open('file://' + os.path.realpath(OUTPUT_HTML))
            except Exception as e:
                print(f"(Could not automatically open the report: {e})")

        except Exception as e:
            print(f"Error writing HTML file: {e}")
    else:
        print("Analysis failed or was interrupted. Could not generate full report.")