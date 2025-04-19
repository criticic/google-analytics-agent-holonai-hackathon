"""
Visualization components for the Google Analytics - Business Intelligence - Agent.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging

logger = logging.getLogger("gabi.web.components")

def render_visualization(config, data):
    """
    Render visualization based on configuration and data using Plotly.
    
    Args:
        config: Dictionary with chart configuration (type, title, axes, etc)
        data: List of dictionaries with the data to visualize
    """
    if not config or not data or len(data) == 0:
        logger.warning("No data available for visualization")
        st.info("No data available for visualization")
        return
    
    try:
        df = pd.DataFrame(data)
        
        chart_type = config.get("chart_type", "").lower()
        title = config.get("title", "Data Visualization")
        
        logger.info(f"Rendering {chart_type} chart: '{title}'")
        
        st.subheader(title)
        
        x_field = config.get("x_field") or config.get("x_axis", {}).get("data_key")
        y_field = config.get("y_field") or config.get("y_axis", {}).get("data_key")
        color_by = config.get("color_by")
        
        logger.debug(f"Chart parameters - x: {x_field}, y: {y_field}, color: {color_by}")
        
        fig = None
        
        if chart_type == "bar" and x_field and y_field and x_field in df.columns and y_field in df.columns:
            fig = px.bar(
                df,
                x=x_field,
                y=y_field,
                color=color_by if color_by and color_by in df.columns else None,
                title=title
            )
            
        elif chart_type == "line" and x_field and y_field and x_field in df.columns and y_field in df.columns:
            fig = px.line(
                df,
                x=x_field,
                y=y_field,
                color=color_by if color_by and color_by in df.columns else None,
                title=title
            )
            
        elif chart_type == "pie":
            values = config.get("values") or y_field
            names = config.get("names") or x_field
            
            if values and names and values in df.columns and names in df.columns:
                fig = px.pie(
                    df,
                    values=values,
                    names=names,
                    title=title
                )
            
        elif chart_type == "scatter" and x_field and y_field and x_field in df.columns and y_field in df.columns:
            fig = px.scatter(
                df,
                x=x_field,
                y=y_field,
                color=color_by if color_by and color_by in df.columns else None,
                title=title
            )
            
        elif chart_type == "heatmap" and x_field and y_field and x_field in df.columns and y_field in df.columns:
            if "value" in df.columns:
                pivot_df = df.pivot(index=y_field, columns=x_field, values="value")
                fig = px.imshow(pivot_df, title=title)
            else:
                cross_tab = pd.crosstab(df[y_field], df[x_field])
                fig = px.imshow(cross_tab, title=title)
                
        elif chart_type == "table" or not chart_type:
            table_columns = config.get("columns", [])
            if table_columns:
                headers = [col.get("header", col.get("data_key", "")) for col in table_columns]
                data_keys = [col.get("data_key", "") for col in table_columns]
                
                filtered_columns = [key for key in data_keys if key in df.columns]
                filtered_df = df[filtered_columns] if filtered_columns else df
                
                header_mapping = dict(zip(filtered_columns, headers[:len(filtered_columns)]))
                filtered_df = filtered_df.rename(columns=header_mapping)
            else:
                filtered_df = df
                
            fig = go.Figure(
                data=[
                    go.Table(
                        header=dict(
                            values=list(filtered_df.columns),
                            fill_color="paleturquoise",
                            align="left",
                            line_color='darkslategray',
                        ),
                        cells=dict(
                            values=[filtered_df[col] for col in filtered_df.columns],
                            fill_color="lavender",
                            align="left",
                            line_color='darkslategray',
                        ),
                    )
                ]
            )
            fig.update_layout(title=title)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            logger.info(f"Successfully rendered {chart_type} visualization")
        else:
            logger.warning(f"Failed to create {chart_type} chart with the provided data")
            st.error(f"Failed to create {chart_type} chart with the provided data.")
            st.dataframe(df, use_container_width=True)
                
    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}")
        st.error(f"Error generating visualization: {str(e)}")
        try:
            st.dataframe(df, use_container_width=True)
        except:
            st.error("Unable to display data table")