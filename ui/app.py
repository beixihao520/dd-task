"""Streamlit UI for DD Analytics Agent with Interactive Chat."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import time
import os

from dd_agent.orchestrator.pipeline import Pipeline
from dd_agent.orchestrator.agent import Agent
from dd_agent.contracts.questions import Question

# Page configuration
st.set_page_config(
    page_title="DD Analytics Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for chat interface
st.markdown("""
<style>
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
    }
    .user-message {
        background-color: #E3F2FD;
        padding: 12px 16px;
        border-radius: 18px 18px 0 18px;
        margin: 8px 0;
        margin-left: auto;
        max-width: 80%;
        border: 1px solid #BBDEFB;
    }
    .assistant-message {
        background-color: #F5F5F5;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 0;
        margin: 8px 0;
        margin-right: auto;
        max-width: 80%;
        border: 1px solid #E0E0E0;
    }
    .thinking-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #666;
        font-style: italic;
        padding: 8px;
    }
    .analysis-result {
        background-color: #FFF8E1;
        padding: 16px;
        border-radius: 10px;
        border-left: 4px solid #FFB300;
        margin: 12px 0;
    }
    .metric-highlight {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .stButton button {
        width: 100%;
        background-color: #4F46E5;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

class ChatMessage:
    """Chat message class."""
    def __init__(self, role: str, content: str, timestamp: str = None, data: Dict = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.data = data or {}

def initialize_session_state():
    """Initialize session state variables."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        # Load data
        data_dir = Path('data/demo')
        with open(data_dir / 'questions.json') as f:
            questions_data = json.load(f)
            questions = [Question.model_validate(q) for q in questions_data]
        
        responses_df = pd.read_csv(data_dir / 'responses.csv')
        
        # Initialize core components
        st.session_state.questions = questions
        st.session_state.responses_df = responses_df
        st.session_state.data_dir = data_dir
        st.session_state.agent = Agent(
            questions=questions,
            responses_df=responses_df,
            data_dir=data_dir
        )
        st.session_state.pipeline = Pipeline(data_dir)
        
        # Chat history
        st.session_state.messages = [
            ChatMessage(
                role="assistant",
                content="👋 Hello! I'm your DD Analytics Agent. I can help you analyze survey data, create segments, and generate insights.\n\nTry asking me things like:\n• Show NPS by region\n• Compare satisfaction by plan\n• Create a segment of enterprise customers\n• Analyze feature usage patterns"
            )
        ]
        
        # Analysis history
        st.session_state.runs = []
        st.session_state.segments = []
        
        # Current state
        st.session_state.thinking = False

def display_chat_message(message: ChatMessage):
    """Display a chat message."""
    if message.role == "user":
        st.markdown(f'<div class="user-message"><strong>You:</strong><br>{message.content}</div>', unsafe_allow_html=True)
    elif message.role == "assistant":
        st.markdown(f'<div class="assistant-message"><strong>🤖 Agent:</strong><br>{message.content}</div>', unsafe_allow_html=True)

def display_analysis_result(result: Dict):
    """Display analysis results in a structured way."""
    with st.container():
        st.markdown('<div class="analysis-result">', unsafe_allow_html=True)
        
        if 'tables' in result and result['tables']:
            for table in result['tables'][:3]:  # Show up to 3 tables
                st.subheader(f"📊 {table.get('title', 'Analysis Results')}")
                
                if 'df' in table and table['df'] is not None:
                    df = pd.DataFrame(table['df'])
                    
                    # Display metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Metric", table.get('metric_type', 'N/A'))
                    with col2:
                        st.metric("Base Size", table.get('base_n', 'N/A'))
                    with col3:
                        if 'dimension' in df.columns and 'metric' in df.columns:
                            top_value = df.nlargest(1, 'metric')['metric'].values[0] if not df.empty else 'N/A'
                            st.metric("Top Value", top_value)
                    
                    # Display table
                    st.dataframe(df, use_container_width=True)
                    
                    # Create visualization
                    if 'dimension' in df.columns and 'metric' in df.columns:
                        fig = px.bar(
                            df,
                            x='dimension',
                            y='metric',
                            title=f"{table.get('metric_type', 'Metric')} by Dimension",
                            color='metric',
                            color_continuous_scale='Viridis'
                        )
                        st.plotly_chart(fig, use_container_width=True)
        
        elif 'plan' in result:
            st.subheader("🤖 Analysis Plan")
            st.write(f"**Rationale**: {result['plan'].get('rationale', 'N/A')}")
            
            for i, intent in enumerate(result['plan'].get('intents', [])):
                with st.expander(f"Step {i+1}: {intent.get('description', 'N/A')}"):
                    st.write(f"**Priority**: {intent.get('priority', 'N/A')}")
                    if intent.get('segments_needed'):
                        st.write(f"**Segments needed**: {', '.join(intent['segments_needed'])}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def process_user_query(query: str):
    """Process user query and generate response."""
    try:
        # Add user message to chat
        st.session_state.messages.append(ChatMessage(role="user", content=query))
        
        # Show thinking indicator
        with st.spinner("🤔 Analyzing your request..."):
            # Determine query type and process
            if query.lower().startswith(('create segment', 'define segment', 'segment of')):
                # Segment creation
                result = st.session_state.agent.build_segment(query)
                if result.ok and result.data:
                    segment = result.data
                    st.session_state.segments.append(segment)
                    
                    response = f"✅ **Segment Created**\n\n**Name**: {segment.name}\n**ID**: {segment.segment_id}\n\n"
                    if segment.notes:
                        response += f"**Notes**: {segment.notes}\n\n"
                    response += "This segment is now available for analysis."
                    
                    st.session_state.messages.append(
                        ChatMessage(
                            role="assistant", 
                            content=response,
                            data={"segment": segment.model_dump()}
                        )
                    )
                else:
                    error_msg = "❌ Failed to create segment. Please try a different definition."
                    if result.errors:
                        error_msg += f"\n\nErrors: {', '.join([str(e) for e in result.errors])}"
                    st.session_state.messages.append(
                        ChatMessage(role="assistant", content=error_msg)
                    )
            
            elif query.lower().startswith(('show', 'analyze', 'compare', 'what is', 'how many', 'plot', 'graph')):
                # Analysis query
                result = st.session_state.pipeline.run_single(query, save_run=True)
                
                if result.success:
                    # Generate response
                    response = "✅ **Analysis Complete**\n\n"
                    
                    if result.execution_result and result.execution_result.tables:
                        table = result.execution_result.tables[0]
                        response += f"**Metric**: {table.metric_type}\n"
                        response += f"**Question**: {table.question_id}\n"
                        response += f"**Base Size**: {table.base_n}\n\n"
                        
                        if hasattr(table, 'df') and table.df is not None:
                            # Summarize findings
                            df = pd.DataFrame(table.df)
                            if 'dimension' in df.columns and 'metric' in df.columns:
                                top = df.nlargest(1, 'metric')
                                bottom = df.nsmallest(1, 'metric')
                                
                                response += "**Key Findings**:\n"
                                response += f"• Highest: {top['dimension'].values[0]} ({top['metric'].values[0]})\n"
                                response += f"• Lowest: {bottom['dimension'].values[0]} ({bottom['metric'].values[0]})\n"
                    
                    else:
                        response += "Analysis completed but no tables were generated."
                    
                    # Save to runs
                    st.session_state.runs.append({
                        'timestamp': datetime.now().isoformat(),
                        'query': query,
                        'run_id': result.run_id,
                        'success': True
                    })
                    
                    # Add to messages with data
                    st.session_state.messages.append(
                        ChatMessage(
                            role="assistant",
                            content=response,
                            data={"analysis_result": result.model_dump() if hasattr(result, 'model_dump') else {}}
                        )
                    )
                else:
                    error_msg = "❌ Analysis failed. Please try rephrasing your query."
                    if result.errors:
                        error_msg += f"\n\nErrors: {', '.join([str(e) for e in result.errors])}"
                    st.session_state.messages.append(
                        ChatMessage(role="assistant", content=error_msg)
                    )
            
            elif query.lower() in ['auto-plan', 'autoplan', 'comprehensive analysis']:
                # Auto-plan
                result = st.session_state.pipeline.run_autoplan(save_run=True, max_cuts=3)
                
                if result.success:
                    response = "🤖 **Auto-Plan Complete**\n\n"
                    response += f"**Rationale**: {result.plan.rationale}\n\n"
                    response += f"**Plan generated {len(result.plan.intents)} analysis steps**\n"
                    
                    # Save to runs
                    st.session_state.runs.append({
                        'timestamp': datetime.now().isoformat(),
                        'query': 'Auto-plan',
                        'run_id': result.run_id,
                        'success': True
                    })
                    
                    st.session_state.messages.append(
                        ChatMessage(
                            role="assistant",
                            content=response,
                            data={"plan": result.plan.model_dump() if hasattr(result.plan, 'model_dump') else {}}
                        )
                    )
                else:
                    st.session_state.messages.append(
                        ChatMessage(
                            role="assistant", 
                            content="❌ Auto-plan failed. Please try again."
                        )
                    )
            
            else:
                # General response
                st.session_state.messages.append(
                    ChatMessage(
                        role="assistant",
                        content="I can help you with:\n\n1. **Analysis**: 'Show NPS by region', 'Compare satisfaction by plan'\n2. **Segments**: 'Create segment of enterprise customers'\n3. **Auto-plan**: 'Run comprehensive analysis'\n\nWhat would you like to do?"
                    )
                )
    
    except Exception as e:
        st.error(f"Error processing query: {str(e)}")
        st.session_state.messages.append(
            ChatMessage(
                role="assistant",
                content=f"❌ Sorry, I encountered an error: {str(e)}\n\nPlease try rephrasing your request."
            )
        )

def main():
    """Main application."""
    # Initialize session state
    initialize_session_state()
    
    # Main header
    st.markdown('<h1 class="main-header">🤖 DD Analytics Agent - Interactive</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Quick Actions")
        
        if st.button("📈 Show NPS by Region", use_container_width=True):
            process_user_query("Show NPS by region")
        
        if st.button("🏢 Create Enterprise Segment", use_container_width=True):
            process_user_query("Create segment of enterprise customers on ENT plan")
        
        if st.button("🔍 Compare Plans", use_container_width=True):
            process_user_query("Compare satisfaction by subscription plan")
        
        if st.button("🤖 Auto-Plan", use_container_width=True):
            process_user_query("Run comprehensive analysis")
        
        st.divider()
        
        st.header("📋 Data Info")
        st.write(f"**Questions**: {len(st.session_state.questions)}")
        st.write(f"**Responses**: {len(st.session_state.responses_df)}")
        
        if st.session_state.segments:
            st.divider()
            st.header("📍 Active Segments")
            for segment in st.session_state.segments[-3:]:
                st.caption(f"• {segment.name}")
        
        if st.session_state.runs:
            st.divider()
            st.header("📜 Recent Runs")
            for run in st.session_state.runs[-5:]:
                st.caption(f"• {run['query'][:30]}...")
        
        st.divider()
        if st.button("🗑️ Clear Chat", type="secondary", use_container_width=True):
            st.session_state.messages = [
                ChatMessage(
                    role="assistant",
                    content="Chat cleared! How can I help you analyze your data today?"
                )
            ]
            st.rerun()
    
    # Main chat interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Chat display area
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Display chat history
        for message in st.session_state.messages:
            display_chat_message(message)
            
            # If message has data, show analysis results
            if message.role == "assistant" and message.data:
                if 'analysis_result' in message.data or 'plan' in message.data:
                    display_analysis_result(message.data)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Quick analysis panel
        st.header("💡 Quick Insights")
        
        # Pre-compute some insights
        if 'quick_insights' not in st.session_state:
            try:
                df = st.session_state.responses_df
                
                # NPS calculation example
                if 'nps_question' in df.columns:
                    promoters = (df['nps_question'] >= 9).sum()
                    detractors = (df['nps_question'] <= 6).sum()
                    total = len(df)
                    nps = ((promoters - detractors) / total * 100) if total > 0 else 0
                    
                    st.markdown(f'<div class="metric-highlight">NPS Score<br><h2>{nps:.1f}</h2></div>', unsafe_allow_html=True)
                
                # Satisfaction
                if 'overall_satisfaction' in df.columns:
                    avg_satisfaction = df['overall_satisfaction'].mean()
                    st.metric("Avg Satisfaction", f"{avg_satisfaction:.1f}/5")
                
                # Response rate
                completion_rate = (df.notna().sum().mean() / len(df.columns)) * 100
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
                
            except:
                st.info("Run an analysis to see quick insights here")
        
        st.divider()
        
        # Example queries
        st.subheader("💬 Try asking:")
        examples = [
            "Show NPS by region",
            "Compare satisfaction by age group",
            "Create segment of frequent users",
            "Analyze feature importance"
        ]
        
        for example in examples:
            if st.button(example, key=f"example_{example}"):
                process_user_query(example)
                st.rerun()
    
    # Chat input at bottom
    st.markdown("---")
    
    col_input1, col_input2 = st.columns([5, 1])
    
    with col_input1:
        user_input = st.text_input(
            "Type your analysis request:",
            placeholder="E.g., 'Show satisfaction by region' or 'Create segment of enterprise customers'",
            key="user_input",
            label_visibility="collapsed"
        )
    
    with col_input2:
        send_button = st.button("Send", type="primary", use_container_width=True)
    
    # Handle send
    if send_button and user_input:
        process_user_query(user_input)
        st.rerun()

if __name__ == "__main__":
    main()