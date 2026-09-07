"""Price candles with live GEX levels for the dashboard's primary strike map.

The module deliberately only renders data prepared by the application layer:
it never calculates gamma or reads a market-data provider. OHLC bars are the
only source for the candles; when they are unavailable the chart reports that
state rather than manufacturing a price history from option snapshots.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from gex.adapters.persistence import store

COLORS = {
    "surface": "#070a13",          # Gexbot terminal deep space
    "card": "#0d1322",
    "ink": "#f8fafc",
    "muted": "#94a3b8",
    "grid": "#161f30",             # Crisp dark terminal grid
    "up": "#00e676",               # Gexbot emerald bull candle
    "down": "#ff1744",             # Gexbot coral bear candle
    "spot": "#ffffff",
    "call_wall": "#00f0ff",        # Electric neon cyan (Call Wall Resistance)
    "call_wall_glow": "rgba(0, 240, 255, 0.28)",
    "put_wall": "#ff2e74",         # Electric neon magenta (Put Wall Support)
    "put_wall_glow": "rgba(255, 46, 116, 0.28)",
    "flip": "#fbbf24",             # Vivid amber gold (Gamma Flip)
    "flip_glow": "rgba(251, 191, 36, 0.22)",
}


def _fmt_gex(val: float) -> str:
    sign = "+" if val > 0 else "-" if val < 0 else ""
    abs_v = abs(val)
    if abs_v >= 1e9:
        return f"{sign}${abs_v / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{sign}${abs_v / 1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{sign}${abs_v / 1e3:.1f}K"
    return f"{sign}${abs_v:.0f}"


def _empty(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, showarrow=False,
        font=dict(color=COLORS["muted"], size=14, family="Inter, sans-serif"),
    )
    fig.update_layout(
        height=620, paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["surface"],
        margin=dict(l=54, r=28, t=50, b=45),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def _wall_stats(chain: pd.DataFrame, strike: float, side: str) -> tuple[float, float, float]:
    """Return GEX, OI and volume at a level without recreating GEX maths."""
    rows = chain[(chain["strike"] == strike) & (chain["type"] == side)]
    if rows.empty:
        return 0.0, 0.0, 0.0
    return (
        float(rows["gex"].sum()) if "gex" in rows else 0.0,
        float(rows["open_interest"].fillna(0).sum()) if "open_interest" in rows else 0.0,
        float(rows["volume"].fillna(0).sum()) if "volume" in rows else 0.0,
    )


def _overlay_levels(
    chain: pd.DataFrame,
    spot: float,
    keys: dict,
) -> tuple[list[float], list[float]]:
    """Resolve the three directional levels without changing GEX calculation."""
    call_levels = keys.get("call_walls")
    put_levels = keys.get("put_supports")
    if isinstance(call_levels, (list, tuple)) and isinstance(put_levels, (list, tuple)):
        return list(map(float, call_levels[:3])), list(map(float, put_levels[:3]))

    if chain.empty or not {"strike", "type", "gex"}.issubset(chain.columns):
        return [], []
    grouped = chain.groupby(["type", "strike"])["gex"].sum()
    calls = grouped[(grouped.index.get_level_values("type") == "C")
                    & (grouped.index.get_level_values("strike") >= spot)
                    & (grouped > 0)]
    puts = grouped[(grouped.index.get_level_values("type") == "P")
                   & (grouped.index.get_level_values("strike") <= spot)
                   & (grouped < 0)]
    return (
        [float(strike) for strike in calls.abs().nlargest(3).index.get_level_values("strike")],
        [float(strike) for strike in puts.abs().nlargest(3).index.get_level_values("strike")],
    )


def _gamma_activity_points(
    snapshots: list[tuple[datetime, pd.DataFrame]] | None,
    spot: float,
    window: float,
) -> list[dict]:
    """Extract dominant positive/negative gamma strikes across intraday snapshots."""
    if not snapshots:
        return []
    points = []
    low, high = spot * (1.0 - window), spot * (1.0 + window)
    for timestamp, chain in snapshots:
        if chain is None or chain.empty or "strike" not in chain or "gex" not in chain:
            continue
        visible = chain[(chain["strike"] >= low) & (chain["strike"] <= high)]
        if visible.empty:
            continue
        for option_type in ("C", "P"):
            side = visible[visible["type"] == option_type]
            if side.empty:
                continue
            ordered = side.sort_values("gex", ascending=(option_type == "P"))
            lead = ordered.iloc[0]
            points.append({
                "timestamp": timestamp,
                "type": option_type,
                "strike": float(lead["strike"]),
                "gex": float(lead["gex"]),
                "open_interest": float(lead.get("open_interest", 0.0) or 0.0),
                "volume": float(lead.get("volume", 0.0) or 0.0),
            })
    return points


def _add_gamma_activity(
    fig: go.Figure,
    points: list[dict],
    transform: Callable[[float], float],
) -> None:
    if not points:
        return
    stamps = sorted({point["timestamp"] for point in points})
    next_timestamp = {stamps[idx]: (stamps[idx + 1] if idx + 1 < len(stamps) else stamps[idx])
                      for idx in range(len(stamps))}
    largest = max((abs(point["gex"]) for point in points), default=1.0) or 1.0
    specs = (("C", "Active call GEX", COLORS["call_wall"]),
             ("P", "Active put GEX", COLORS["put_wall"]))
    for option_type, name, color in specs:
        side = [point for point in points if point["type"] == option_type]
        if not side:
            continue
        rail_x: list[object] = []
        rail_y: list[object] = []
        for point in side:
            end = next_timestamp[point["timestamp"]]
            if end == point["timestamp"]:
                continue
            rail_x.extend([point["timestamp"], end, None])
            shown_strike = float(transform(point["strike"]))
            rail_y.extend([shown_strike, shown_strike, None])
        if rail_x:
            fig.add_trace(go.Scatter(
                x=rail_x, y=rail_y, mode="lines", name=name,
                line=dict(color=color, width=3), opacity=0.45, hoverinfo="skip",
                legendgroup=f"activity-{option_type}",
            ))
        custom = np.asarray([[point["gex"], point["open_interest"], point["volume"]]
                             for point in side])
        sizes = [8 + 14 * np.sqrt(abs(point["gex"]) / largest) for point in side]
        fig.add_trace(go.Scatter(
            x=[point["timestamp"] for point in side],
            y=[float(transform(point["strike"])) for point in side],
            mode="markers", name=f"{name} points", showlegend=False,
            marker=dict(size=sizes, color=color, opacity=0.88,
                        line=dict(color=COLORS["surface"], width=1.5)),
            customdata=custom, legendgroup=f"activity-{option_type}",
            hovertemplate=(
                f"<b style='color:{color}'>● {name}</b><br>"
                "Snapshot: <b>%{x|%H:%M:%S}</b><br>"
                "Strike: <b>%{y:,.2f}</b><br>"
                "GEX: %{customdata[0]:+,.0f}<br>"
                "Open interest: %{customdata[1]:,.0f}<br>"
                "Volume: %{customdata[2]:,.0f}<extra></extra>"
            ),
        ))


def merge_relayout_ranges(
    relayout: Mapping | None,
    current_figure: Mapping | None,
) -> dict:
    """Complete partial Plotly relayout events with the other axis range."""
    merged = dict(relayout or {})
    layout = current_figure.get("layout", {}) if isinstance(current_figure, Mapping) else {}
    if not isinstance(layout, Mapping):
        return merged

    for axis in ("xaxis", "yaxis"):
        if merged.get(f"{axis}.autorange") is True:
            continue
        has_range = (
            isinstance(merged.get(f"{axis}.range"), (list, tuple))
            or (f"{axis}.range[0]" in merged and f"{axis}.range[1]" in merged)
        )
        if has_range:
            continue
        axis_layout = layout.get(axis, {})
        previous_range = axis_layout.get("range") if isinstance(axis_layout, Mapping) else None
        if isinstance(previous_range, (list, tuple)) and len(previous_range) == 2:
            merged[f"{axis}.range"] = list(previous_range)
    return merged


def _apply_relayout(fig: go.Figure, relayout: Mapping | None) -> None:
    """Persist an intentional pan/zoom across chart refreshes without snapping back."""
    if not relayout:
        return
    if relayout.get("dragmode") in {"pan", "zoom"}:
        fig.update_layout(dragmode=relayout["dragmode"])
    # Handle an explicit reset per axis without resetting the other axis.
    if relayout.get("autosize"):
        fig.update_layout(autosize=True)
    if relayout.get("xaxis.autorange") is True:
        fig.update_xaxes(autorange=True)
    if relayout.get("yaxis.autorange") is True:
        fig.update_yaxes(autorange=True)

    # Check both formats of relayoutData in Dash:
    # Format A: {"xaxis.range[0]": val0, "xaxis.range[1]": val1}
    # Format B: {"xaxis.range": [val0, val1]}
    x_range = relayout.get("xaxis.range")
    if isinstance(x_range, (list, tuple)) and len(x_range) == 2:
        fig.update_xaxes(range=list(x_range), autorange=False)
    elif relayout.get("xaxis.autorange") is not True:
        x0 = relayout.get("xaxis.range[0]")
        x1 = relayout.get("xaxis.range[1]")
        if x0 is not None and x1 is not None:
            fig.update_xaxes(range=[x0, x1], autorange=False)

    y_range = relayout.get("yaxis.range")
    if isinstance(y_range, (list, tuple)) and len(y_range) == 2:
        try:
            fig.update_yaxes(range=[float(y_range[0]), float(y_range[1])], autorange=False)
        except (ValueError, TypeError):
            pass
    elif relayout.get("yaxis.autorange") is not True:
        y0 = relayout.get("yaxis.range[0]")
        y1 = relayout.get("yaxis.range[1]")
        if y0 is not None and y1 is not None:
            try:
                fig.update_yaxes(range=[float(y0), float(y1)], autorange=False)
            except (ValueError, TypeError):
                pass


def _time_rangebreaks(times: pd.Series) -> list[dict]:
    """Hide only gaps absent from the stored candles, never live data."""
    if len(times) < 2:
        return []
    ordered = pd.Series(pd.to_datetime(times).sort_values().unique())
    gaps = ordered.diff()
    breaks = []
    for idx in gaps[gaps > pd.Timedelta(minutes=5)].index:
        breaks.append({"bounds": [ordered.loc[idx - 1], ordered.loc[idx]]})
    return breaks


def build_options_overlay(
    symbol: str,
    chain: pd.DataFrame | None,
    spot: float | None,
    gamma_flip: float | None,
    keys: dict | None,
    day: str,
    window: float,
    transform: Callable[[float | np.ndarray], float | np.ndarray] | None = None,
    show_price: bool = True,
    show_call_wall: bool = True,
    show_put_wall: bool = True,
    show_gamma_flip: bool = True,
    snapshots: list[tuple[datetime, pd.DataFrame]] | None = None,
    relayout: dict | None = None,
    timeframe: str = "2d",
) -> go.Figure:
    """Build the interactive candle/GEX overlay for the selected session."""
    prices = store.load_prices(symbol, day)
    needed = {"timestamp", "open", "high", "low", "close"}
    if prices.empty and symbol in {"ES", "NQ"}:
        prices = store.load_prices({"ES": "SPX", "NQ": "NDX"}[symbol], day)
    if prices.empty:
        return _empty(f"No hay velas OHLC reales disponibles para {symbol} en la sesión {day}.")
    if chain is None or chain.empty:
        chain = pd.DataFrame(columns=["strike", "type", "gex", "open_interest", "volume"])
    if not spot or spot <= 0:
        spot = float(prices["close"].iloc[-1])

    # Keep the previous saved session available for a centered multi-session view.
    all_p_days = store.price_days(symbol)
    previous_days = [saved_day for saved_day in all_p_days if saved_day < day]
    if previous_days and timeframe in {"2d", "all"}:
        prev_day = previous_days[-1]
        prev_prices = store.load_prices(symbol, prev_day)
        if not prev_prices.empty and needed.issubset(prev_prices.columns):
            prev_prices = prev_prices.dropna(subset=list(needed)).copy()
            prev_prices["timestamp"] = pd.to_datetime(prev_prices["timestamp"])
            if not prices.empty and needed.issubset(prices.columns):
                prices["timestamp"] = pd.to_datetime(prices["timestamp"])
                prices = pd.concat([prev_prices.tail(390), prices], ignore_index=True)
            else:
                prices = prev_prices

    if prices.empty or not needed.issubset(prices.columns):
        return _empty(f"No hay velas OHLC reales disponibles para {symbol} en la sesión {day}.")

    prices = prices.dropna(subset=list(needed)).copy()
    if prices.empty:
        return _empty(f"No hay velas OHLC válidas disponibles para {symbol} en la sesión {day}.")
    prices["timestamp"] = pd.to_datetime(prices["timestamp"])
    prices = prices.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    if timeframe == "5m":
        prices = (prices.set_index("timestamp")
                  .resample("5min")
                  .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
                  .dropna()
                  .reset_index())
    timeframe_limits = {"1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4),
                        "1d": pd.Timedelta(days=1), "2d": pd.Timedelta(days=2)}
    if timeframe in timeframe_limits:
        cutoff = prices["timestamp"].max() - timeframe_limits[timeframe]
        prices = prices[prices["timestamp"] >= cutoff]
    if prices.empty:
        return _empty(f"No hay velas disponibles para la temporalidad {timeframe}.")
    transform = transform or (lambda value: value)

    def tx(value):
        return transform(value)

    times = prices["timestamp"]
    fig = go.Figure()

    if show_price:
        o_tx = tx(prices["open"].to_numpy())
        h_tx = tx(prices["high"].to_numpy())
        l_tx = tx(prices["low"].to_numpy())
        c_tx = tx(prices["close"].to_numpy())
        fig.add_trace(go.Candlestick(
            x=times, open=o_tx, high=h_tx, low=l_tx, close=c_tx,
            name="Price",
            whiskerwidth=0.7,
            increasing_line_color=COLORS["up"],
            decreasing_line_color=COLORS["down"],
            increasing_fillcolor=COLORS["up"],
            decreasing_fillcolor=COLORS["down"],
            increasing_line_width=1.8,
            decreasing_line_width=1.8,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d %H:%M}</b><br>"
                "Open: %{open:,.2f}<br>"
                "High: %{high:,.2f}<br>"
                "Low: %{low:,.2f}<br>"
                "Close: %{close:,.2f}<extra></extra>"
            ),
        ))

    keys = keys or {}
    call_levels, put_levels = _overlay_levels(chain, float(spot), keys)
    level_specs = [
        (show_call_wall, call_levels, "Call Wall", "C", COLORS["call_wall"], COLORS["call_wall_glow"], "solid"),
        (show_put_wall, put_levels, "Put Wall", "P", COLORS["put_wall"], COLORS["put_wall_glow"], "solid"),
        (show_gamma_flip, "gamma_flip", "Gamma Flip", None, COLORS["flip"], COLORS["flip_glow"], "dash"),
    ]
    resolved_levels = []
    for enabled, values, label, side, color, glow_color, dash in level_specs:
        if not enabled:
            continue
        if values == "gamma_flip":
            raw_values = [gamma_flip] if gamma_flip is not None else []
        else:
            raw_values = values
        for rank, raw_value in enumerate(raw_values):
            if raw_value is None:
                continue
            shown_label = label if rank == 0 else f"{label} {rank + 1}"
            if side:
                gex, oi, volume = _wall_stats(chain, float(raw_value), side)
            else:
                nearby = chain[np.isclose(chain["strike"], float(raw_value))]
                gex = float(nearby["gex"].sum()) if "gex" in nearby else 0.0
                oi = float(nearby["open_interest"].fillna(0).sum()) if "open_interest" in nearby else 0.0
                volume = float(nearby["volume"].fillna(0).sum()) if "volume" in nearby else 0.0
            resolved_levels.append((float(raw_value), shown_label, color, glow_color, gex, oi, volume, dash))

    # Determine largest GEX magnitude to scale wall vivacity and thickness
    largest_gex = max((abs(item[4]) for item in resolved_levels), default=0.0) or 1.0

    annotations = []
    for raw_value, label, color, glow_color, gex, oi, volume, dash in resolved_levels:
        rel_strength = min(1.0, max(0.15, abs(gex) / largest_gex if largest_gex else 0.5))
        dist_pct = ((raw_value - spot) / spot) * 100.0 if spot else 0.0
        dist_str = f"{dist_pct:+.2f}%"
        gex_badge = _fmt_gex(gex)
        strength_pct = int(rel_strength * 100)

        # 1. Halo / Glow trace behind wall (gives vivid visual presence of wall size)
        halo_width = float(2.5 + 2.5 * np.sqrt(rel_strength))
        fig.add_trace(go.Scatter(
            x=times, y=np.repeat(float(tx(raw_value)), len(times)),
            mode="lines", showlegend=False,
            line=dict(color=glow_color, width=halo_width),
            opacity=0.55,
            hoverinfo="skip",
        ))

        # 2. Main Wall Line with interactive hover card
        line_width = float(1.25 + 1.25 * np.sqrt(rel_strength))
        custom = np.repeat([[gex, oi, volume]], len(times), axis=0)

        fig.add_trace(go.Scatter(
            x=times, y=np.repeat(float(tx(raw_value)), len(times)),
            mode="lines", name=label,
            line=dict(color=color, width=line_width, dash=dash),
            customdata=custom,
            hovertemplate=(
                f"<b style='color:{color}'>━━ {label} ━━</b><br>"
                "Strike: <b>%{y:,.2f}</b> (" + dist_str + " vs Spot)<br>"
                "GEX: %{customdata[0]:+,.0f}<br>"
                f"Fuerza Muro: <b>{strength_pct}%</b><br>"
                "Open interest: %{customdata[1]:,.0f}<br>"
                "Volume: %{customdata[2]:,.0f}<extra></extra>"
            ),
        ))

        # 3. Right-side level badge
        annotations.append(dict(
            xref="paper", yref="y",
            x=1.005, y=float(tx(raw_value)),
            text=f"<b>{label}</b>: {float(tx(raw_value)):,.1f} ({gex_badge})",
            showarrow=False,
            font=dict(color="#000000", size=10, family="Inter, monospace"),
            align="left",
            bgcolor=color,
            bordercolor="#0b0f19",
            borderwidth=1,
            borderpad=3,
            opacity=0.92,
        ))

    activity_window = min(max(window, 0.015), 0.04)
    _add_gamma_activity(fig, _gamma_activity_points(snapshots, spot, activity_window), tx)

    shown_spot = float(tx(float(spot)))
    spot_custom = np.repeat([[0.0, 0.0, 0.0, 0, "0.00%"]], len(times), axis=0)
    fig.add_trace(go.Scatter(
        x=times, y=np.repeat(shown_spot, len(times)),
        mode="lines", name="Current price",
        line=dict(color=COLORS["spot"], width=1.5, dash="dot"),
        customdata=spot_custom,
        hovertemplate=(
            "<b style='color:#ffffff'>● Current price (Spot)</b><br>"
            "Price: <b>%{y:,.2f}</b><extra></extra>"
        ),
    ))

    # Spot right-side badge
    annotations.append(dict(
        xref="paper", yref="y",
        x=1.005, y=shown_spot,
        text=f"<b>Spot</b>: {shown_spot:,.1f}",
        showarrow=False,
        font=dict(color="#000000", size=10, family="Inter, monospace"),
        align="left",
        bgcolor="#ffffff",
        bordercolor="#0b0f19",
        borderwidth=1,
        borderpad=3,
        opacity=0.95,
    ))

    focus_window = min(max(window, 0.012), 0.025)
    level_values = [item[0] for item in resolved_levels]
    range_low = min([spot * (1 - focus_window), *level_values])
    range_high = max([spot * (1 + focus_window), *level_values])
    if range_high <= range_low:
        range_low, range_high = spot * 0.98, spot * 1.02
    padding = max((range_high - range_low) * 0.06, spot * 0.001)

    fig.update_layout(
        title=dict(
            text=f"<b>{symbol}</b> · Live price + GEX levels · {day}",
            x=0.01, xanchor="left",
            font=dict(color=COLORS["ink"], size=15, family="Inter, sans-serif"),
        ),
        height=620,
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        margin=dict(l=64, r=130, t=56, b=48),
        font=dict(color=COLORS["muted"], family="Inter, sans-serif"),
        hovermode="closest",
        dragmode="pan",
        hoverlabel=dict(
            bgcolor="rgba(11, 15, 25, 0.95)",
            bordercolor=COLORS["grid"],
            font=dict(color=COLORS["ink"], family="Inter, monospace", size=12),
        ),
        legend=dict(
            orientation="h", y=1.09, x=0,
            font=dict(color=COLORS["muted"], size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            title="Time",
            gridcolor=COLORS["grid"],
            zeroline=False,
            fixedrange=False,
            rangeslider=dict(visible=False),
            range=[times.iloc[0], times.iloc[-1]],
            autorange=False,
            rangebreaks=_time_rangebreaks(times),
        ),
        yaxis=dict(
            title="Price / strike",
            gridcolor=COLORS["grid"],
            zeroline=False,
            fixedrange=False,
            range=sorted(tx(np.asarray([range_low - padding, range_high + padding]))),
            autorange=False,
            side="left",
        ),
        annotations=annotations,
    )
    _apply_relayout(fig, relayout)
    return fig
