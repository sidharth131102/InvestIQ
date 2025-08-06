import yfinance as yf
import plotly.graph_objects as go

def plot_investment_trend(ticker):
    try:
        data = yf.download(ticker, period="1mo", interval="1d")
        if data.empty:
            return None, "No market data available."

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data.index, y=data['Close'],
            mode='lines+markers', name=f"{ticker} Closing Price"
        ))
        fig.update_layout(
            title=f"{ticker} - Last 1 Month Trend",
            xaxis_title="Date", yaxis_title="Closing Price",
            template="plotly_white", height=300
        )

        latest_price = data['Close'].iloc[-1]
        first_price = data['Close'].iloc[0]
        change = ((latest_price - first_price) / first_price) * 100
        trend = "upward 📈" if change > 0 else "downward 📉"
        summary = f"{ticker} is currently {trend}, with a latest closing price of {latest_price:.2f} USD ({change:.2f}% over last month)."

        return fig, summary
    except Exception:
        return None, "No market data available."
